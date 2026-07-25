"""The five analyst agents. Each frames the same context through its own lens."""

from __future__ import annotations

from aegis_shared.contracts import (
    AgentType,
    FinancialAnalystOutput,
    MacroAnalystOutput,
    NewsAnalystOutput,
    QuantAnalystOutput,
    RiskOfficerOutput,
)

from ..tools import ToolContext
from .base import AnalystAgent, _memory_block


class NewsAnalyst(AnalystAgent):
    agent_type = AgentType.NEWS
    output_model = NewsAnalystOutput

    def system_prompt(self) -> str:
        return (
            "You are a News Intelligence Analyst. Analyze news, earnings call tone, and "
            "SEC filings to identify sentiment trends. Distinguish signal from noise. "
            "Every claim must be grounded in the provided evidence."
        )

    def user_prompt(self, ctx: ToolContext) -> str:
        heads = "\n".join(
            f"- [{h['source']}] {h['title']} (sentiment {h['sentiment']:+.2f})"
            for h in ctx.news.headlines
        )
        risks = "\n".join(f"- {r}" for r in ctx.filings.risk_factors)
        return (
            f"Ticker: {ctx.ticker}\n"
            f"Aggregate news sentiment: {ctx.news.aggregate_sentiment:+.2f}\n"
            f"Headlines:\n{heads}\n"
            f"Filing risk factors ({ctx.filings.latest_form}):\n{risks}\n\n"
            f"{_memory_block(ctx)}\n\n"
            "Produce bullish_points, bearish_points, a sentiment_score in [-1,1], "
            "and your confidence in [0,1]."
        )


class FinancialAnalyst(AnalystAgent):
    agent_type = AgentType.FINANCIAL
    output_model = FinancialAnalystOutput

    def system_prompt(self) -> str:
        return (
            "You are a Financial Analyst. Assess revenue growth, margins, profitability, "
            "leverage, cash flow, and valuation. Be rigorous and quantitative."
        )

    def user_prompt(self, ctx: ToolContext) -> str:
        f = ctx.fundamentals
        return (
            f"Ticker: {ctx.ticker}\n"
            f"Revenue growth YoY: {f.revenue_growth_yoy:.1%}\n"
            f"Gross margin: {f.gross_margin:.1%} | Net margin: {f.net_margin:.1%} | "
            f"FCF margin: {f.fcf_margin:.1%}\n"
            f"Debt/Equity: {f.debt_to_equity:.2f} | P/E: {f.pe_ratio:.1f}\n\n"
            f"{_memory_block(ctx)}\n\n"
            "Produce fundamentals_score and valuation_score in [0,1], strengths, "
            "weaknesses, and confidence in [0,1]."
        )


class QuantAnalyst(AnalystAgent):
    agent_type = AgentType.QUANT
    output_model = QuantAnalystOutput

    def system_prompt(self) -> str:
        return (
            "You are a Quantitative Analyst. Evaluate momentum, volatility, risk-adjusted "
            "returns, and technical trend structure. Report metrics precisely."
        )

    def user_prompt(self, ctx: ToolContext) -> str:
        m = ctx.market
        return (
            f"Ticker: {ctx.ticker}\n"
            f"Last price: {m.last_price} | 3M momentum: {m.momentum_3m:.1%} | "
            f"12M momentum: {m.momentum_12m:.1%}\n"
            f"Annualized volatility: {m.volatility_annual:.1%} | Sharpe: {m.sharpe:.2f} | "
            f"Beta: {m.beta:.2f} | Max drawdown: {m.max_drawdown:.1%}\n\n"
            f"{_memory_block(ctx)}\n\n"
            "Produce quant_score in [0,1], technical_signals, a risk_metrics map, "
            "and confidence in [0,1]."
        )


class MacroAnalyst(AnalystAgent):
    agent_type = AgentType.MACRO
    output_model = MacroAnalystOutput

    def system_prompt(self) -> str:
        return (
            "You are a Macro Analyst. Weigh interest rates, inflation, growth conditions, "
            "and sector outlook. Connect the macro regime to this specific name."
        )

    def user_prompt(self, ctx: ToolContext) -> str:
        return (
            f"Ticker: {ctx.ticker}\n"
            f"Sector volatility proxy (annualized): {ctx.market.volatility_annual:.1%}\n"
            f"Beta to market: {ctx.market.beta:.2f}\n\n"
            f"{_memory_block(ctx)}\n\n"
            "Assess the macro backdrop. Produce macro_score in [0,1], opportunities, "
            "threats, and confidence in [0,1]."
        )


class RiskOfficer(AnalystAgent):
    """Adversarial agent — always argues the bear case to prevent groupthink."""

    agent_type = AgentType.RISK
    output_model = RiskOfficerOutput

    def system_prompt(self) -> str:
        return (
            "You are the Risk Officer. Your job is NOT to support the investment. "
            "Your job is to find weaknesses: valuation, geopolitical, concentration, "
            "earnings, and market risk. Be adversarial and specific. Assume the bull "
            "case is wrong and stress-test it."
        )

    def user_prompt(self, ctx: ToolContext) -> str:
        f, m = ctx.fundamentals, ctx.market
        risks = "\n".join(f"- {r}" for r in ctx.filings.risk_factors)
        return (
            f"Ticker: {ctx.ticker}\n"
            f"P/E: {f.pe_ratio:.1f} | Debt/Equity: {f.debt_to_equity:.2f} | "
            f"Beta: {m.beta:.2f} | Volatility: {m.volatility_annual:.1%} | "
            f"Max drawdown: {m.max_drawdown:.1%}\n"
            f"Disclosed risk factors:\n{risks}\n\n"
            f"{_memory_block(ctx)}\n\n"
            "Produce overall_risk_score in [0,1] (higher = more dangerous), dangers, "
            "stress_scenarios, and confidence in [0,1]."
        )


def build_analysts() -> list[AnalystAgent]:
    return [
        NewsAnalyst(),
        FinancialAnalyst(),
        QuantAnalyst(),
        MacroAnalyst(),
        RiskOfficer(),
    ]
