"""Live filings provider backed by SEC EDGAR.

Pipeline: ticker -> CIK (cached) -> latest submissions -> most recent 10-K primary
document -> extract the "Item 1A. Risk Factors" section -> top sentences.

Degradation ladder:
  1. Full risk-factor extraction from the latest 10-K.
  2. If extraction fails but submissions load, return recent filing summaries.
  3. If CIK/submissions fail entirely, raise -> factory falls back to synthetic.

SEC requires a descriptive ``User-Agent`` with contact info; requests without it are
throttled/blocked (403).
"""

from __future__ import annotations

import html
import re

from .base import FilingsData

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{folder}/{doc}"
_MAX_DOC_BYTES = 15_000_000  # cap 10-K download size (iXBRL docs are large)


class EdgarFilings:
    def __init__(self, user_agent: str, timeout: float = 15.0) -> None:
        if not user_agent or "@" not in user_agent:
            raise RuntimeError(
                "SEC_USER_AGENT must be set to 'Name Company email@example.com'"
            )
        self._headers = {"User-Agent": user_agent}
        self._timeout = timeout
        self._cik_map: dict[str, str] | None = None

    def fetch(self, ticker: str) -> FilingsData:
        import requests

        cik = self._resolve_cik(ticker, requests)
        resp = requests.get(
            _SUBMISSIONS_URL.format(cik=cik), headers=self._headers, timeout=self._timeout
        )
        resp.raise_for_status()
        recent = resp.json()["filings"]["recent"]

        forms = recent["form"]
        latest_form = forms[0] if forms else "N/A"

        risk_factors = self._extract_risk_factors(cik, recent, requests)
        if not risk_factors:
            risk_factors = self._summarize_filings(recent)

        return FilingsData(
            risk_factors=risk_factors, latest_form=latest_form, source="edgar"
        )

    # -- CIK resolution --------------------------------------------------------

    def _resolve_cik(self, ticker: str, requests) -> str:
        if self._cik_map is None:
            resp = requests.get(_TICKERS_URL, headers=self._headers, timeout=self._timeout)
            resp.raise_for_status()
            self._cik_map = {
                row["ticker"].upper(): str(row["cik_str"]).zfill(10)
                for row in resp.json().values()
            }
        cik = self._cik_map.get(ticker.upper())
        if cik is None:
            raise RuntimeError(f"No EDGAR CIK for {ticker}")
        return cik

    # -- Risk factor extraction ------------------------------------------------

    def _extract_risk_factors(self, cik: str, recent: dict, requests) -> list[str]:
        idx = self._latest_index(recent, wanted="10-K")
        if idx is None:
            return []
        folder = recent["accessionNumber"][idx].replace("-", "")
        doc = recent["primaryDocument"][idx]
        url = _ARCHIVE_URL.format(cik_int=int(cik), folder=folder, doc=doc)
        try:
            resp = requests.get(url, headers=self._headers, timeout=self._timeout)
            resp.raise_for_status()
            raw = resp.content[:_MAX_DOC_BYTES].decode("utf-8", errors="ignore")
        except Exception:
            return []
        return self._parse_item_1a(raw)

    @staticmethod
    def _latest_index(recent: dict, wanted: str) -> int | None:
        for i, form in enumerate(recent["form"]):
            if form == wanted:
                return i
        return None

    @staticmethod
    def _parse_item_1a(document: str) -> list[str]:
        text = html.unescape(re.sub(r"<[^>]+>", " ", document)).replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)

        # "Item 1A. Risk Factors" appears once in the table of contents (a tiny block)
        # and again as the real section. Take the LAST heading to skip the TOC.
        starts = [
            m.end()
            for m in re.finditer(r"item\s*1a\.?\s*risk factors", text, re.IGNORECASE)
        ]
        if not starts:
            return []
        tail = text[starts[-1]:]
        end = re.search(r"item\s*1b\b|item\s*2\b", tail, re.IGNORECASE)
        block = tail[: end.start()] if end else tail[:8000]
        if len(block) < 200:
            return []
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", block)
            if 60 <= len(s.strip()) <= 400
        ]
        return sentences[:5]

    @staticmethod
    def _summarize_filings(recent: dict, limit: int = 5) -> list[str]:
        forms = recent["form"]
        dates = recent["filingDate"]
        return [f"{forms[i]} filed {dates[i]}" for i in range(min(limit, len(forms)))]
