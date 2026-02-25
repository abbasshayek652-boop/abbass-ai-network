from agents.utils.circuit import CircuitBreaker, CircuitBreakerConfig


def test_circuit_breaker_trips_after_failures():
    breaker = CircuitBreaker(CircuitBreakerConfig(max_failures=3, window_secs=10))
    breaker.record("qc")
    breaker.record("qc")
    assert breaker.tripped is False
    breaker.record("qc")
    assert breaker.tripped is True

