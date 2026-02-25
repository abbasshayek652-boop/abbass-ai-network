# Mother AI (Windows 10 Quickstart)

This repository runs a FastAPI control plane (`gateway.py`) that loads agents from `registry.json`.

## 1) Single intended entrypoint

Use:

```bash
python -m mother_ai.run
```

That command starts Uvicorn on `0.0.0.0:${PORT:-8000}`.

---

## 2) What was failing and what was fixed

### Root cause A: unclear startup command
- **Problem**: multiple run styles (`uvicorn gateway:app`, `make run`, Replit docs) caused confusion.
- **Fix**: standardized on one command: `python -m mother_ai.run`.

### Root cause B: incomplete root dependencies
- **Problem**: root `requirements.txt` was too small for the actual imports used by `gateway_pkg/` and agents.
- **Fix**: aligned root `requirements.txt` with runtime dependencies used by this project.

### Root cause C: hard to verify installation before running server
- **Problem**: no easy preflight check from CLI.
- **Fix**: added `--smoke-test` to entrypoint:
  ```bash
  python -m mother_ai.run --smoke-test
  ```
  It validates imports and registry hydration, then prints JSON.

---

## 3) Install (fresh Windows 10 machine)

Open **PowerShell** in the project folder.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run once as admin:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 4) Configure environment

1. Copy env template:

```powershell
Copy-Item .env.example .env
```

2. Edit `.env` and set at minimum:
- `MOTHER_API_KEY`
- `MOTHER_JWT_SECRET`

For minimal boot + health check, defaults are enough. Exchange and LinkedIn secrets are only needed when using those features.

---

## 5) Run

```powershell
python -m mother_ai.run
```

Server URL:
- `http://127.0.0.1:8000`

---

## 6) Smallest smoke test (required)

### Preflight smoke test (no server)

```powershell
python -m mother_ai.run --smoke-test
```

Expected output shape:

```json
{"ok": true, "app": "Mother AI Gateway", "agents_loaded": ["..."]}
```

### HTTP health check (running server)

```powershell
curl http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

---

## 7) Minimal API verification

After starting the server:

```powershell
curl http://127.0.0.1:8000/readyz
```

Expected:

```json
{"ready":true}
```

---

## 8) Notes

- `MOTHER_BINANCE_KEY` / `MOTHER_BINANCE_SECRET` are required **only** for live exchange operations.
- LinkedIn env vars are required only for `/agents/linkedin/*` endpoints.
- Keep `.env` private and never commit secrets.

---

## Phase 2 Implemented

- `/agents/*` control surface (list, detail, start/stop, status, logs tail)
- `/console/*` UI-friendly health + recent events
- `/webhooks/n8n` with `X-Webhook-Token` (`MOTHER_WEBHOOK_TOKEN`)

### Sample commands

```bash
curl http://127.0.0.1:8010/agents
```

```bash
curl http://127.0.0.1:8010/console/health
```

```bash
curl -H "X-Webhook-Token: $MOTHER_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"status","agent_key":"learning","meta":{}}' \
  http://127.0.0.1:8010/webhooks/n8n
```

### DB note

Phase 2 adds new tables (`PnLHistory`, `ConfigHistory`, `Lead`). No Alembic migrations are required; the SQLite metadata is initialized on startup.
