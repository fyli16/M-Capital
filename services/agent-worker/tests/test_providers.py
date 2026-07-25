from app.config import Settings
from app.tools.providers import DataProviders, build_providers
from app.tools.providers.factory import _Fallback
from app.tools.providers.synthetic import SyntheticMarketData


def test_default_is_synthetic():
    providers = build_providers(Settings(data_provider="synthetic"))
    md = providers.market.fetch("NVDA")
    assert md.source == "synthetic"
    assert md.last_price > 0


def test_synthetic_is_deterministic():
    a = SyntheticMarketData().fetch("AAPL")
    b = SyntheticMarketData().fetch("AAPL")
    assert a == b


def test_live_missing_sec_user_agent_falls_back_to_synthetic_filings():
    # No SEC_USER_AGENT -> EDGAR construction fails -> synthetic filings, no crash.
    providers = build_providers(Settings(data_provider="live", sec_user_agent=""))
    assert isinstance(providers, DataProviders)
    filings = providers.filings.fetch("NVDA")
    assert filings.source == "synthetic"


class _Boom:
    def fetch(self, ticker: str):
        raise RuntimeError("feed down")


def test_fallback_wrapper_uses_synthetic_on_error():
    wrapped = _Fallback("market", _Boom(), SyntheticMarketData())
    result = wrapped.fetch("TSLA")
    assert result.source == "synthetic"
