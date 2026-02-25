from __future__ import annotations

import datetime as dt
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from adapters.exchange.router import ExchangeRouter
from agents.modes.shadow import ModeState, ShadowStats
from agents.utils.circuit import CircuitBreaker, CircuitBreakerConfig
from agents.utils.market_rules import conform_qty, min_notional
from agents.utils.portfolio import Portfolio, Position
from ai.base_agent import Agent
from ai.settings import settings
from ai.utils.retry import with_retry
from data.quality import update_history, validate_ohlcv, validate_ticker
from governance.audit_rules import post_trade_audit, pre_trade_audit
from oms.algos import execute_twap
from oms.execution import Executor
from oms.orders import OrderIntent
from persistence.db import add_audit, add_trade, init_db
from persistence.snapshot import load_latest_snapshot, write_snapshot
from risk.cooldowns import Cooldown, CooldownState
from risk.portfolio_limits import TrailingStopTracker, dynamic_notional_cap, risk_parity_targets
from risk.rules import RiskCaps, check_pre_trade
from strategies.base import Strategy
from strategies.momentum_ema import MomentumEMAStrategy
from telemetry.alerts import notify_webhook
from telemetry.metrics import (
    canary_live_ratio,
    cash_usdt,
    data_qc_fail_total,
    exposure_usdt,
    last_score,
    orders_total,
    snapshot_writes_total,
    ticks_total,
)
from telemetry.tracing import build_tracer
from utils.schedule import in_trading_session
from utils.secrets import decrypt

LOGGER = logging.getLogger(__name__)

_STRATEGIES: Dict[str, type[Strategy]] = {"momentum_ema": MomentumEMAStrategy}


class CryptoTradingAgent(Agent):
    """Resilient crypto trading agent with routing, QC, and governance."""

    name = "crypto"
    description = "Scores markets and executes trades with strict controls."

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.paper_mode: bool = bool(self.config.get("paper", True))
        self.mode: str = str(self.config.get("mode", "shadow" if self.paper_mode else "canary"))
        self.allowed_pairs: List[str] = list(
            self.config.get("allowed_pairs", ["BTC/USDT", "ETH/USDT", "BNB/USDT"])
        )
        self.timeframe: str = str(self.config.get("timeframe", "1m"))
        self.tick_seconds: int = int(self.config.get("tick_seconds", 15))
        self.fee_bps: int = int(self.config.get("fee_bps", 10))
        self.slippage_bps: int = int(self.config.get("slippage_bps", 5))
        self.safety_cash_pct: float = float(self.config.get("safety_cash_pct", 0.95))
        self.max_positions_per_symbol: int = int(self.config.get("max_positions_per_symbol", 1))
        self.strategy_name: str = str(self.config.get("strategy", "momentum_ema"))
        self.router_exchanges: List[str] = list(self.config.get("router_exchanges", ["binance"]))
        self.session_windows: List[tuple[str, str]] = [
            (str(start), str(end))
            for start, end in self.config.get("session_windows", [["00:00", "23:59"]])
        ]
        self.duplicate_cooldown_seconds: int = int(self.config.get("duplicate_cooldown_seconds", 20))
        self.confirm_live: Optional[str] = self.config.get("confirm_live")
        self.webhook_url: Optional[str] = self.config.get("webhook_url") or settings.webhook_url
        self.db_url: str = str(self.config.get("db_url") or settings.db_url)
        self.starting_cash: float = float(self.config.get("starting_cash") or settings.paper_starting_cash)
        self.quote_currency: str = "USDT"
        self.canary_live_fraction: float = float(self.config.get("canary_live_fraction", 0.1))
        self.trailing_stop_pct: float = float(self.config.get("trailing_stop_pct", 0.0))
        self.twap_seconds: int = int(self.config.get("twap_seconds", 20))
        self.resume: bool = bool(self.config.get("resume", True))
        self.max_latency_ms: int = int(self.config.get("max_latency_ms", 1200))
        self.deviation_sigma: float = float(self.config.get("deviation_sigma", 5.0))
        self.max_gap_pct: float = float(self.config.get("max_gap_pct", 0.07))
        self.bypass_canary: bool = bool(self.config.get("bypass_canary", False))
        self.otlp_endpoint: Optional[str] = self.config.get("otlp_endpoint") or settings.otlp_endpoint
        self.fernet_key: Optional[str] = self.config.get("fernet_key") or settings.fernet_key

        self.cooldown_cfg = Cooldown(duplicate_secs=self.duplicate_cooldown_seconds)
        self.cooldowns = CooldownState()
        self.risk_caps = RiskCaps(
            max_notional_per_trade=float(self.config.get("max_notional_per_trade", 15.0)),
            max_positions_per_symbol=int(self.config.get("max_positions_per_symbol", 1)),
            max_total_exposure_usdt=float(self.config.get("max_total_exposure_usdt", 150.0)),
            max_drawdown_pct_session=float(self.config.get("max_drawdown_pct_session", 0.08)),
            per_symbol_exposure_usdt=float(self.config.get("per_symbol_exposure_usdt", 50.0)),
        )

        self.router: ExchangeRouter | None = None
        self.executor: Executor | None = None
        self.strategy: Strategy | None = None
        self.mode_state = ModeState(self.mode, self.canary_live_fraction, ShadowStats())
        self.trailing_stop = TrailingStopTracker(self.trailing_stop_pct)
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self.tracer = build_tracer(self.name, self.otlp_endpoint)

        self.markets: Dict[str, Any] = {}
        self.portfolio: Portfolio | None = None
        self.db_engine = None
        self.last_tick_ts: float | None = None
        self.last_error: str | None = None
        self.last_scores: Dict[str, float] = {}
        self.last_balance: Dict[str, Any] | None = None
        self.price_cache: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.vol_cache: Dict[str, float] = {}
        self.session_start_equity: float | None = None
        self.session_high_equity: float | None = None
        self.session_low_equity: float | None = None
        self.kill_switch_triggered = False
        self.tick_counter = 0
        self.snapshot_every = max(1, int(self.config.get("snapshot_every", 1)))

    async def start(self) -> None:
        if self.running:
            return
        self.strategy = self._load_strategy(self.strategy_name)
        api_key = decrypt(settings.binance_key, self.fernet_key)
        api_secret = decrypt(settings.binance_secret, self.fernet_key)
        self.router = ExchangeRouter(
            self.router_exchanges,
            paper=self.paper_mode,
            api_key=api_key,
            api_secret=api_secret,
            agent=self.name,
        )
        await self.router.init()
        self.markets = await with_retry(lambda: self.router.fetch_markets())
        primary_adapter = self.router.primary.adapter if self.router.primary else None
        self.executor = Executor(primary_adapter, self.paper_mode, fee_bps=self.fee_bps)
        self.db_engine = init_db(self.db_url)
        add_audit(self.db_engine, "info", self.name, "start", "agent starting")

        if self.paper_mode:
            self.portfolio = Portfolio(cash_usdt=self.starting_cash)
        else:
            await self._validate_live_mode(api_key, api_secret)

        if self.resume:
            await self._restore_snapshot()

        self.running = True
        self.last_error = None
        self.last_tick_ts = None
        self.kill_switch_triggered = False
        equity = self._compute_equity()
        self.session_start_equity = equity
        self.session_high_equity = equity
        self.session_low_equity = equity
        self.logger.info(
            "%s started",
            self.__class__.__name__,
            extra={"mode": self.mode, "paper": self.paper_mode},
        )

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        add_audit(self.db_engine, "info", self.name, "stop", "agent stopping")
        self.logger.info("%s stopped", self.__class__.__name__)

    async def status(self) -> Dict[str, Any]:
        positions = self._positions_snapshot()
        exposures, total_exposure = self._exposures_from_cache()
        cash_val = self._current_cash()
        status_payload = {
            "running": self.running,
            "mode": self.mode,
            "allowed_pairs": self.allowed_pairs,
            "open_positions": positions,
            "cash": {self.quote_currency: cash_val},
            "last_tick_ts": self.last_tick_ts,
            "last_error": self.last_error,
            "last_scores": self.last_scores,
            "drawdown": self._current_drawdown(),
            "session_active": self._session_active(),
            "total_exposure": total_exposure,
            "kill_switch": self.kill_switch_triggered,
            "circuit": self.circuit_breaker.tripped,
            "snapshot_interval": self.snapshot_every,
        }
        if self.router:
            status_payload["router_health"] = self.router.health_snapshot()
        return status_payload

    async def on_tick(self) -> None:
        if not self.running or not self.strategy or not self.executor or not self.router:
            return
        if self.kill_switch_triggered or self.circuit_breaker.tripped:
            return
        if not self._session_active():
            self.logger.debug("Outside trading session; skipping tick")
            return
        if self.mode_state.should_halt() and not self.bypass_canary:
            self.logger.warning("Canary safeguards triggered; halting live trading")
            return

        async with self.tracer.span_async("on_tick"):
            ticks_total.labels(self.name).inc()
            self.last_tick_ts = time.time()
            try:
                await self._refresh_balances()
            except Exception as exc:  # pragma: no cover - network path
                self.last_error = str(exc)
                self.logger.exception("Failed to refresh balances: %s", exc)
                self.circuit_breaker.record("balance")
                return

            exposures, total_exposure = self._exposures_from_cache()
            vol_targets = risk_parity_targets(self.allowed_pairs, self.vol_cache, self.risk_caps)

            for symbol in self.allowed_pairs:
                async with self.tracer.span_async("fetch_market_data"):
                    try:
                        ohlcv = await with_retry(
                            lambda sym=symbol: self.router.fetch_ohlcv(sym, self.timeframe, 120),
                            attempts=3,
                            base_delay=0.5,
                        )
                        ticker = await with_retry(
                            lambda sym=symbol: self.router.best_quote(sym, "buy"),
                            attempts=3,
                            base_delay=0.5,
                        )
                    except Exception as exc:  # pragma: no cover - data path
                        self.last_error = str(exc)
                        self.logger.exception("Market data fetch failed for %s: %s", symbol, exc)
                        self.circuit_breaker.record("market")
                        continue

                ok, reason = validate_ohlcv(symbol, ohlcv, max_gap_pct=self.max_gap_pct)
                if not ok:
                    data_qc_fail_total.labels(self.name, symbol).inc()
                    self.logger.warning("QC rejected ohlcv", extra={"symbol": symbol, "reason": reason})
                    self.circuit_breaker.record("qc")
                    continue
                venue_name, ticker_payload = ticker
                price = float(ticker_payload.get("last") or ticker_payload.get("close"))
                update_history(self.price_history[symbol], price)
                ok, reason = validate_ticker(price, self.price_history[symbol], deviation_sigma=self.deviation_sigma)
                if not ok:
                    data_qc_fail_total.labels(self.name, symbol).inc()
                    self.logger.warning("QC rejected ticker", extra={"symbol": symbol, "reason": reason})
                    self.circuit_breaker.record("qc")
                    continue
                self.price_cache[symbol] = price

                try:
                    features = await self.strategy.compute_features(ohlcv)
                    sig = await self.strategy.signal(features)
                except Exception as exc:  # pragma: no cover
                    self.last_error = str(exc)
                    self.logger.exception("Strategy failure for %s: %s", symbol, exc)
                    self.circuit_breaker.record("strategy")
                    continue

                score = float(sig.get("score", 0.0))
                decision = str(sig.get("signal", "hold"))
                self.last_scores[symbol] = score
                last_score.labels(self.name, symbol).set(score)
                self.logger.info(
                    "decision",
                    extra={"symbol": symbol, "score": score, "signal": decision, "venue": venue_name},
                )
                self.vol_cache[symbol] = float(features.get("volatility", 0.2))

                position_qty = self._position_qty(symbol)
                has_position = position_qty > 1e-9
                if self.trailing_stop.update(symbol, price, has_position):
                    await self._handle_sell(symbol, price, position_qty, exposures, total_exposure)
                    continue

                if decision == "buy" and position_qty <= 1e-9:
                    await self._handle_buy(
                        symbol,
                        price,
                        features,
                        exposures,
                        total_exposure,
                        vol_targets.get(symbol, self.risk_caps.max_notional_per_trade),
                    )
                elif decision == "sell" and position_qty > 1e-9:
                    await self._handle_sell(symbol, price, position_qty, exposures, total_exposure)

            await self._update_metrics()
            await self._check_drawdown()
            self.tick_counter += 1
            if self.tick_counter % self.snapshot_every == 0:
                await self._persist_snapshot()

    def _load_strategy(self, name: str) -> Strategy:
        try:
            strategy_cls = _STRATEGIES[name]
        except KeyError as exc:
            raise ValueError(f"Unknown strategy {name}") from exc
        return strategy_cls(timeframe=self.timeframe)

    async def _validate_live_mode(self, api_key: Optional[str], api_secret: Optional[str]) -> None:
        if self.paper_mode:
            return
        if not api_key or not api_secret:
            raise RuntimeError("Live mode requires API credentials")
        if self.confirm_live != "I UNDERSTAND":
            raise RuntimeError("Live mode requires confirm_live=I UNDERSTAND")
        if not self.config.get("dry_run_passed", False):
            raise RuntimeError("Dry run must pass before enabling live mode")
        if self.mode == "live" and not self.bypass_canary:
            raise RuntimeError("Enable canary mode before full live trading")
        balance = await with_retry(lambda: self.router.fetch_balance())
        self.last_balance = balance
        if not isinstance(balance, dict) or "free" not in balance:
            raise RuntimeError("Failed to load live balances")

    async def _restore_snapshot(self) -> None:
        if not self.db_engine:
            return
        snapshot = load_latest_snapshot(self.db_engine, self.name)
        if not snapshot:
            return
        self.logger.info("Restoring snapshot state", extra={"ts": snapshot.get("ts")})
        self.last_scores = snapshot.get("last_scores", {})
        self.price_cache = snapshot.get("price_cache", {})
        self.price_history = defaultdict(list, snapshot.get("price_history", {}))
        self.vol_cache = snapshot.get("vol_cache", {})
        self.last_tick_ts = snapshot.get("last_tick_ts")
        if self.paper_mode and self.portfolio:
            pf_data = snapshot.get("portfolio", {})
            self.portfolio.cash_usdt = pf_data.get("cash", self.portfolio.cash_usdt)
            positions = pf_data.get("positions", {})
            self.portfolio.positions = {
                sym: Position(**data) for sym, data in positions.items()
            }

    async def _persist_snapshot(self) -> None:
        if not self.db_engine:
            return
        payload = {
            "ts": time.time(),
            "last_scores": self.last_scores,
            "price_cache": self.price_cache,
            "price_history": self.price_history,
            "vol_cache": self.vol_cache,
            "last_tick_ts": self.last_tick_ts,
        }
        if self.paper_mode and self.portfolio:
            payload["portfolio"] = {
                "cash": self.portfolio.cash_usdt,
                "positions": {
                    sym: {"qty": pos.qty, "avg_price": pos.avg_price}
                    for sym, pos in self.portfolio.positions.items()
                },
            }
        write_snapshot(self.db_engine, self.name, payload)
        snapshot_writes_total.labels(self.name).inc()

    async def _refresh_balances(self) -> None:
        if self.paper_mode or not self.router:
            return
        self.last_balance = await with_retry(lambda: self.router.fetch_balance())

    def _session_active(self) -> bool:
        return in_trading_session(dt.datetime.now(), self.session_windows)

    def _positions_snapshot(self) -> Dict[str, Dict[str, float]]:
        if self.paper_mode and self.portfolio:
            return {
                symbol: {"qty": pos.qty, "avg_price": pos.avg_price}
                for symbol, pos in self.portfolio.positions.items()
            }
        if self.last_balance:
            total = self.last_balance.get("total", {})
            return {
                symbol: {"qty": float(total.get(self._base(symbol), 0.0)), "avg_price": 0.0}
                for symbol in self.allowed_pairs
                if float(total.get(self._base(symbol), 0.0)) > 0
            }
        return {}

    def _position_qty(self, symbol: str) -> float:
        if self.paper_mode and self.portfolio:
            pos: Position | None = self.portfolio.positions.get(symbol)
            return pos.qty if pos else 0.0
        if self.last_balance:
            total = self.last_balance.get("total", {})
            if isinstance(total, dict):
                return float(total.get(self._base(symbol), 0.0))
        return 0.0

    def _available_cash(self) -> float:
        if self.paper_mode and self.portfolio:
            return self.portfolio.cash_usdt * self.safety_cash_pct
        if self.last_balance:
            free = self.last_balance.get("free", {})
            if isinstance(free, dict):
                return float(free.get(self.quote_currency, 0.0)) * self.safety_cash_pct
        return 0.0

    async def _handle_buy(
        self,
        symbol: str,
        price: float,
        features: Dict[str, float],
        exposures: Dict[str, float],
        total_exposure: float,
        target_notional: float,
    ) -> None:
        if self.cooldowns.too_soon(symbol, "buy", self.cooldown_cfg):
            return
        if self._position_qty(symbol) > 0 and self.max_positions_per_symbol <= 1:
            return
        budget = min(self._available_cash(), self.risk_caps.max_notional_per_trade)
        if budget <= 0:
            return
        volatility = float(features.get("volatility", 0.2))
        cap = dynamic_notional_cap(symbol, volatility, self.risk_caps, target_notional)
        notional = min(budget, cap)
        qty = conform_qty(symbol, notional / price if price else 0.0, self.markets)
        notional = qty * price
        minimum = max(min_notional(symbol, self.markets), 0.0)
        if qty <= 0 or notional <= 0 or notional < minimum:
            return
        ok, reason = check_pre_trade(symbol, price, qty, self.risk_caps, exposures, total_exposure)
        if not ok:
            self._record_risk_reject(symbol, "buy", reason)
            return
        await self._execute_order(symbol, "buy", qty, price)

    async def _handle_sell(
        self,
        symbol: str,
        price: float,
        position_qty: float,
        exposures: Dict[str, float],
        total_exposure: float,
    ) -> None:
        if position_qty <= 0:
            return
        if self.cooldowns.too_soon(symbol, "sell", self.cooldown_cfg):
            return
        qty = conform_qty(symbol, position_qty, self.markets)
        notional = qty * price
        if qty <= 0 or notional <= 0:
            return
        ok, reason = check_pre_trade(symbol, price, qty, self.risk_caps, exposures, total_exposure)
        if not ok:
            self._record_risk_reject(symbol, "sell", reason)
            return
        await self._execute_order(symbol, "sell", qty, price)

    async def _execute_order(self, symbol: str, side: str, qty: float, price: float) -> None:
        if not self.executor or not self.router:
            return
        intent = OrderIntent(
            symbol=symbol,
            side=side,
            type="market",
            qty=qty,
            client_id=f"{self.name}-{int(time.time())}-{side}",
        )
        pre_trade_audit(
            self.db_engine,
            self.name,
            {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "mode": self.mode,
                "paper": self.paper_mode,
            },
        )
        live_qty, shadow_qty = self.mode_state.split(qty)
        if self.mode == "shadow":
            self.mode_state.record_shadow({"symbol": symbol, "side": side, "qty": qty, "price": price})
            return
        responses: List[Dict[str, Any]] = []
        health = self.router.health_snapshot()
        latency_breach = any(h.get("latency_ms", 0.0) > self.max_latency_ms for h in health.values())
        if live_qty > 0:
            live_intent = OrderIntent(
                symbol=symbol,
                side=side,
                type="market",
                qty=live_qty,
                client_id=f"{intent.client_id}-live",
            )
            try:
                if (
                    self.twap_seconds > 5
                    and live_qty * price > min_notional(symbol, self.markets) * 2
                    and not latency_breach
                ):
                    responses = await execute_twap(
                        self.router,
                        self.executor,
                        live_intent,
                        total_notional=live_qty * price,
                        price=price,
                        seconds=self.twap_seconds,
                        slippage_bps=self.slippage_bps,
                    )
                else:
                    success, payload, venue = await self.router.execute(
                        live_intent,
                        self.executor,
                        slippage_bps=self.slippage_bps,
                    )
                    if success:
                        payload["venue"] = venue
                        responses.append(payload)
                self.circuit_breaker.reset()
            except Exception as exc:
                self.last_error = str(exc)
                self.logger.exception("Order execution failed", extra={"symbol": symbol, "side": side})
                add_audit(
                    self.db_engine,
                    "error",
                    self.name,
                    "order_error",
                    f"{symbol} {side} error: {exc}",
                )
                self.mode_state.record_error()
                if self.webhook_url:
                    await notify_webhook(self.webhook_url, {"event": "order_error", "detail": str(exc)})
                self.circuit_breaker.record("execution")
                return
        if shadow_qty > 0:
            self.mode_state.record_shadow({"symbol": symbol, "side": side, "qty": shadow_qty, "price": price})
            canary_live_ratio.labels(self.name, symbol).set(live_qty / (qty or 1))
        else:
            canary_live_ratio.labels(self.name, symbol).set(1.0 if live_qty > 0 else 0.0)

        for payload in responses:
            filled = float(payload.get("filled", live_qty))
            price_used = float(payload.get("price", price))
            fee = float(payload.get("fee", 0.0))
            order_id = str(payload.get("orderId", "unknown"))
            if self.paper_mode and self.portfolio:
                if side == "buy":
                    self.portfolio.buy(symbol, filled, price_used, fee)
                else:
                    self.portfolio.sell(symbol, filled, price_used, fee)
            orders_total.labels(self.name, symbol, side, "paper" if self.paper_mode else "live").inc()
            add_trade(
                self.db_engine,
                ts=time.time(),
                symbol=symbol,
                side=side,
                qty=filled,
                price=price_used,
                fee=fee,
                order_id=order_id,
                paper=self.paper_mode,
            )
            post_trade_audit(
                self.db_engine,
                self.name,
                {
                    "symbol": symbol,
                    "side": side,
                    "qty": filled,
                    "price": price_used,
                    "fee": fee,
                    "order_id": order_id,
                },
            )

    def _exposures_from_cache(self) -> tuple[Dict[str, float], float]:
        exposures: Dict[str, float] = {}
        total = 0.0
        for symbol, qty in self._positions_qty_map().items():
            price = self.price_cache.get(symbol)
            if price is None:
                continue
            notional = price * qty
            exposures[symbol] = notional
            total += notional
        return exposures, total

    def _positions_qty_map(self) -> Dict[str, float]:
        if self.paper_mode and self.portfolio:
            return {symbol: pos.qty for symbol, pos in self.portfolio.positions.items()}
        if self.last_balance:
            total = self.last_balance.get("total", {})
            if isinstance(total, dict):
                return {
                    symbol: float(total.get(self._base(symbol), 0.0))
                    for symbol in self.allowed_pairs
                }
        return {}

    async def _update_metrics(self) -> None:
        exposures, _ = self._exposures_from_cache()
        cash_value = self._current_cash()
        for symbol in self.allowed_pairs:
            exposure_usdt.labels(self.name, symbol).set(exposures.get(symbol, 0.0))
        cash_usdt.labels(self.name).set(cash_value)

    def _current_cash(self) -> float:
        if self.paper_mode and self.portfolio:
            return self.portfolio.cash_usdt
        if self.last_balance:
            free = self.last_balance.get("free", {})
            if isinstance(free, dict):
                return float(free.get(self.quote_currency, 0.0))
        return 0.0

    async def _check_drawdown(self) -> None:
        equity = self._compute_equity()
        if equity is None:
            return
        if self.session_high_equity is None or equity > self.session_high_equity:
            self.session_high_equity = equity
        if self.session_low_equity is None or equity < self.session_low_equity:
            self.session_low_equity = equity
        self.mode_state.update_drawdown(self.session_start_equity or equity, equity)
        if (
            self.session_high_equity
            and equity < self.session_high_equity * (1 - self.risk_caps.max_drawdown_pct_session)
        ):
            await self._trigger_kill_switch("drawdown")

    def _compute_equity(self) -> Optional[float]:
        exposures, total = self._exposures_from_cache()
        price_known = len(exposures) > 0 or not self._positions_qty_map()
        if not price_known and self.paper_mode:
            return self.portfolio.cash_usdt if self.portfolio else None
        return self._current_cash() + total

    def _current_drawdown(self) -> Optional[float]:
        if not self.session_high_equity:
            return None
        equity = self._compute_equity()
        if equity is None:
            return None
        return 1 - (equity / self.session_high_equity)

    async def _trigger_kill_switch(self, reason: str) -> None:
        if self.kill_switch_triggered:
            return
        self.kill_switch_triggered = True
        self.running = False
        message = f"Kill switch engaged: {reason}"
        self.logger.error(message)
        add_audit(self.db_engine, "error", self.name, "kill_switch", message)
        if self.webhook_url:
            await notify_webhook(self.webhook_url, {"event": "kill_switch", "reason": reason})

    def _record_risk_reject(self, symbol: str, side: str, reason: str) -> None:
        detail = f"Risk reject {symbol} {side}: {reason}"
        self.logger.info(detail)
        add_audit(self.db_engine, "warning", self.name, "risk_reject", detail)
        self.circuit_breaker.record("risk")

    def _base(self, symbol: str) -> str:
        return symbol.split("/")[0]

