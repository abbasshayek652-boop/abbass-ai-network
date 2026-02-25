"""Interactive helper to create a populated `.env` file for Mother AI.

The script asks for the most common configuration values (API keys, tokens,
database URLs, etc.) and writes them to `.env`.  It keeps sensible defaults so
the whole stack can run locally without additional input, while still allowing
operators to provide production credentials when needed.

Usage
-----

```bash
python scripts/configure.py           # prompts for each value
python scripts/configure.py --env-file deploy/.env
python scripts/configure.py --accept-defaults  # non-interactive defaults
```

The command is intentionally dependency-free so it can run before the virtual
environment is created.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Iterable, Mapping

DEFAULT_ENV_PATH = Path(".env")


@dataclass(frozen=True)
class Prompt:
    """Single configuration prompt description."""

    key: str
    message: str
    default: str | None = None
    secret: bool = False


PROMPTS: tuple[Prompt, ...] = (
    Prompt("MOTHER_ENV", "Environment name", "dev"),
    Prompt("MOTHER_API_KEY", "Gateway API key (x-api-key)", "change-me", secret=True),
    Prompt("MOTHER_JWT_SECRET", "JWT secret for dashboard login", "change-me", secret=True),
    Prompt("MOTHER_LOG_LEVEL", "Python log level", "INFO"),
    Prompt("MOTHER_DASHBOARD_ORIGIN", "Dashboard origin for CORS", "http://localhost:5173"),
    Prompt("MOTHER_REDIS_URL", "Redis URL", "redis://localhost:6379/0"),
    Prompt("MOTHER_DB_URL", "Trading DB URL", "sqlite:///mother_trades.db"),
    Prompt("MOTHER_LEARNING_DB", "Learning engine DB URL", "sqlite:///mother_learning.db"),
    Prompt("MOTHER_TELEGRAM_TOKEN", "Telegram bot token", secret=True),
    Prompt("MOTHER_TELEGRAM_ADMINS", "Telegram admin user IDs (comma separated)", ""),
    Prompt("MOTHER_TELEGRAM_OPERATORS", "Telegram operator user IDs (comma separated)", ""),
    Prompt("MOTHER_BINANCE_KEY", "Binance API key (live trading)", secret=True),
    Prompt("MOTHER_BINANCE_SECRET", "Binance API secret (live trading)", secret=True),
    Prompt("MOTHER_OTLP_ENDPOINT", "OTLP collector endpoint", ""),
    Prompt("MOTHER_FERNET_KEY", "Fernet key for encrypted secrets", "", secret=True),
)


def load_existing_values(path: Path) -> dict[str, str]:
    """Parse an existing env file so the operator can amend values easily."""

    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8").splitlines()
    loaded: dict[str, str] = {}
    for line in content:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        loaded[key.strip()] = raw_value.strip()
    return loaded


def _prompt_user(prompt: Prompt, *, accept_defaults: bool, default: str | None) -> str:
    """Collect a single value from stdin, honouring defaults and secrets."""

    default = default or prompt.default or ""
    if accept_defaults:
        return default

    suffix = f" [{default}]" if default else ""
    text = f"{prompt.message}{suffix}: "
    try:
        if prompt.secret:
            value = getpass(text)
        else:
            value = input(text)
    except EOFError:
        # When stdin is not interactive fall back to default.
        return default
    except KeyboardInterrupt:  # pragma: no cover - user aborted manually
        print("\nAborted by user", file=sys.stderr)
        raise SystemExit(1) from None

    value = value.strip()
    return value or default


def collect_values(
    prompts: Iterable[Prompt],
    *,
    accept_defaults: bool,
    existing: Mapping[str, str],
) -> dict[str, str]:
    """Ask the operator for each prompt and return the resulting mapping."""

    collected: dict[str, str] = {}
    for prompt in prompts:
        collected[prompt.key] = _prompt_user(
            prompt,
            accept_defaults=accept_defaults,
            default=existing.get(prompt.key),
        )
    return collected


def write_env_file(path: Path, values: Mapping[str, str]) -> None:
    """Persist the gathered values to a dotenv-style file."""

    lines = [f"{key}={value}" for key, value in values.items() if value != ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_inputs(values: Mapping[str, str]) -> list[str]:
    """Return warnings for obviously unsafe placeholder values."""

    warnings: list[str] = []
    for prompt in PROMPTS:
        value = values.get(prompt.key, "").strip()
        if not value:
            continue
        if prompt.secret and value.lower() in {"change-me", "changeme"}:
            warnings.append(f"Value for {prompt.key} still set to placeholder; update before production use.")
    return warnings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate Mother AI environment file")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Destination for the generated environment file (default: .env)",
    )
    parser.add_argument(
        "--accept-defaults",
        action="store_true",
        help="Do not prompt; use default values for every field",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(list(argv or []))
    existing = load_existing_values(args.env_file)
    values = collect_values(
        PROMPTS,
        accept_defaults=args.accept_defaults,
        existing=existing,
    )
    args.env_file.parent.mkdir(parents=True, exist_ok=True)
    write_env_file(args.env_file, values)
    print(f"Environment file written to {args.env_file}")

    warnings = validate_inputs(values)
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  * {warning}")

    masked_summary = []
    for prompt in PROMPTS:
        value = values.get(prompt.key, "")
        if prompt.secret and value:
            masked_value = "*" * max(4, len(value) // 2)
        else:
            masked_value = value or "<empty>"
        masked_summary.append(f"  - {prompt.key} = {masked_value}")

    print("Captured values:\n" + "\n".join(masked_summary))


if __name__ == "__main__":
    main(sys.argv[1:])

