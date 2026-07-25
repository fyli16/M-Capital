"""Data tools that feed the analysts.

The provider functions here return **deterministic synthetic data** seeded by ticker.
They are stand-ins with the same interface a real integration would expose
(yfinance / Alpha Vantage for prices, EDGAR for filings, a news API for headlines).
Swapping in real providers is a drop-in change behind ``gather_tool_context``.
"""

from .context import ToolContext, gather_tool_context

__all__ = ["ToolContext", "gather_tool_context"]
