"""Pull key stats for the Cover & Assumptions and Trading Comps tabs.

Usage:
    python company_snapshot_v2.py                 # print to console
    python company_snapshot_v2.py --xlsx out.xlsx # also write both tabs (needs openpyxl)
"""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Diageo's NYSE ADR. The London line is "DGE.L" and is quoted in pence (GBp).
DIAGEO_TICKER = "DEO"

PEER_TICKERS = {
    "RI.PA": "Pernod Ricard",           # Euronext Paris, EUR
    "RCO.PA": "Rémy Cointreau",         # Euronext Paris, EUR
    "CPR.MI": "Davide Campari-Milano",  # Borsa Italiana, EUR
    "STZ": "Constellation Brands",      # NYSE, USD
}

# Yahoo FX tickers giving the USD value of 1 unit of the currency.
FX_TICKERS = {"EUR": "EURUSD=X", "GBP": "GBPUSD=X"}

# Yahoo quotes some lines in minor units: currency -> (major currency, divisor).
MINOR_UNITS = {"GBp": ("GBP", 100), "GBX": ("GBP", 100)}

# Ordinary shares per ADR. Kept for reference (e.g. if DEO is ever cross-checked
# directly against DGE.L, where the ordinary-share count and the ADR-share count
# genuinely differ by this ratio) but NOT used in the sanity check below — Yahoo's
# sharesOutstanding for DEO is already ADR-share-equivalent, verified against its
# own market_cap field (see get_company_snapshot).
ADR_RATIOS = {"DEO": 4}

NUMERIC_COLS = [
    "price", "market_cap", "shares_outstanding", "total_debt", "total_cash",
    "ebitda", "total_revenue", "enterprise_value_yahoo", "enterprise_value_computed",
    "beta", "trailing_pe", "forward_pe", "week52_low", "week52_high",
]


@dataclass(frozen=True)
class CompanySnapshot:
    ticker: str
    name: str | None
    exchange: str | None
    sector: str | None
    industry: str | None
    quote_currency: str | None      # currency the share price is quoted in
    financial_currency: str | None  # currency the financial statements are reported in
    price: float | None
    market_cap: float | None
    shares_outstanding: float | None
    total_debt: float | None        # financial currency
    total_cash: float | None        # financial currency
    ebitda: float | None            # financial currency, trailing
    total_revenue: float | None     # financial currency, trailing
    enterprise_value_yahoo: float | None     # Yahoo's precomputed EV; kept for comparison only
    enterprise_value_computed: float | None  # market_cap + debt - cash, only when currencies match
    beta: float | None
    trailing_pe: float | None
    forward_pe: float | None
    week52_low: float | None
    week52_high: float | None
    fetched_at_utc: str

    def to_frame(self) -> pd.DataFrame:
        """Two-column Field/Value table, easy to paste or write into a sheet."""
        return pd.DataFrame(list(asdict(self).items()), columns=["Field", "Value"])


def _fetch_info(ticker: str, retries: int = 3, backoff: float = 2.0) -> dict:
    """Fetch Yahoo's info dict, retrying on empty/failed responses (Yahoo rate-limits often)."""
    for attempt in range(1, retries + 1):
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as exc:  # yfinance raises assorted network/HTTP/JSON errors
            logger.warning("%s: fetch attempt %d/%d failed: %s", ticker, attempt, retries, exc)
            info = {}
        if info.get("currentPrice") or info.get("regularMarketPrice"):
            return info
        if attempt < retries:
            time.sleep(backoff * attempt)
    # Yahoo returns a near-empty dict for unknown tickers rather than raising.
    raise ValueError(f"No price data returned for {ticker!r}; check the ticker or retry later.")


def get_company_snapshot(ticker: str) -> CompanySnapshot:
    """Fetch a trimmed, typed snapshot for `ticker`. Raises ValueError if nothing usable comes back."""
    info = _fetch_info(ticker)
    price = info.get("currentPrice") or info.get("regularMarketPrice")

    quote_ccy = info.get("currency")
    fin_ccy = info.get("financialCurrency")
    market_cap = info.get("marketCap")
    shares = info.get("sharesOutstanding")
    total_debt = info.get("totalDebt")
    total_cash = info.get("totalCash")

    # Native-currency EV is only valid when debt/cash and market cap share a currency.
    ev_computed = None
    if None not in (market_cap, total_debt, total_cash) and quote_ccy == fin_ccy:
        ev_computed = market_cap + total_debt - total_cash

    # ADR sanity check: Yahoo's sharesOutstanding for ADR tickers is already
    # ADR-share-equivalent (verified against DEO: price x shares matches
    # Yahoo's own market_cap to within 0.001%), so no ratio adjustment is needed here.
    if market_cap and shares and price:
        implied = price * shares
        if abs(implied / market_cap - 1) > 0.05:
            logger.warning(
                "%s: price x shares (%.3g) differs from Yahoo's market cap (%.3g) by more than 5%%; "
                "investigate before trusting either.",
                ticker, implied, market_cap,
            )

    if quote_ccy != fin_ccy:
        logger.info("%s: quote currency %s != financial currency %s", ticker, quote_ccy, fin_ccy)

    return CompanySnapshot(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName"),
        exchange=info.get("fullExchangeName") or info.get("exchange"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        quote_currency=quote_ccy,
        financial_currency=fin_ccy,
        price=price,
        market_cap=market_cap,
        shares_outstanding=shares,
        total_debt=total_debt,
        total_cash=total_cash,
        ebitda=info.get("ebitda"),
        total_revenue=info.get("totalRevenue"),
        enterprise_value_yahoo=info.get("enterpriseValue"),
        enterprise_value_computed=ev_computed,
        beta=info.get("beta"),
        trailing_pe=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        week52_low=info.get("fiftyTwoWeekLow"),
        week52_high=info.get("fiftyTwoWeekHigh"),
        fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def get_snapshots(tickers: list[str]) -> dict[str, CompanySnapshot]:
    """Fetch a snapshot per ticker, skipping (and logging) any that fail."""
    snapshots = {}
    for ticker in tickers:
        try:
            snapshots[ticker] = get_company_snapshot(ticker)
        except ValueError as exc:
            logger.warning("Skipping %s: %s", ticker, exc)
    return snapshots


def snapshots_to_frame(snapshots: dict[str, CompanySnapshot]) -> pd.DataFrame:
    """One row per company, with numeric columns coerced so missing values become NaN, not None."""
    df = pd.DataFrame([asdict(s) for s in snapshots.values()])
    if not df.empty:
        df[NUMERIC_COLS] = df[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    return df


@lru_cache(maxsize=None)
def get_usd_rate(currency: str) -> float:
    """USD value of 1 unit of `currency` (handles minor units like GBp). Cached per run."""
    if currency == "USD":
        return 1.0
    if currency in MINOR_UNITS:
        major, divisor = MINOR_UNITS[currency]
        return get_usd_rate(major) / divisor

    fx_ticker = FX_TICKERS.get(currency)
    if fx_ticker is None:
        raise ValueError(f"No FX ticker configured for currency {currency!r}; add it to FX_TICKERS.")

    closes = yf.Ticker(fx_ticker).history(period="5d")["Close"].dropna()
    if closes.empty:
        raise ValueError(f"Could not fetch FX rate for {fx_ticker!r}.")
    return float(closes.iloc[-1])


def _rate_or_nan(currency: object) -> float:
    if not isinstance(currency, str):
        return float("nan")
    try:
        return get_usd_rate(currency)
    except ValueError as exc:
        logger.warning("%s", exc)
        return float("nan")


def _major_rate_or_nan(currency: object) -> float:
    """Like _rate_or_nan, but maps minor units (GBp) to their major currency (GBP) first."""
    if isinstance(currency, str) and currency in MINOR_UNITS:
        currency = MINOR_UNITS[currency][0]
    return _rate_or_nan(currency)


def add_usd_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add explicit USD columns and EV multiples.

    Price converts at the quote-currency rate (pence-aware). Market cap converts at the major
    currency's rate, since Yahoo reports it in major units even when the price is in pence
    (verify this for any .L ticker you add). Debt, cash, EBITDA and revenue convert at the
    financial-currency rate, because Yahoo reports them in a different currency for some lines.
    """
    if df.empty:
        return df
    df = df.copy()

    quote_fx = df["quote_currency"].map(_rate_or_nan)
    fin_fx = df["financial_currency"].map(_rate_or_nan)
    major_fx = df["quote_currency"].map(_major_rate_or_nan)
    df["quote_fx_to_usd"] = quote_fx
    df["financial_fx_to_usd"] = fin_fx

    df["price_usd"] = df["price"] * quote_fx
    df["market_cap_usd"] = df["market_cap"] * major_fx
    df["net_debt_usd"] = (df["total_debt"] - df["total_cash"]) * fin_fx
    df["enterprise_value_usd"] = df["market_cap_usd"] + df["net_debt_usd"]
    df["ebitda_usd"] = df["ebitda"] * fin_fx
    df["revenue_usd"] = df["total_revenue"] * fin_fx

    df["ev_to_ebitda"] = df["enterprise_value_usd"] / df["ebitda_usd"].where(df["ebitda_usd"] > 0)
    df["ev_to_revenue"] = df["enterprise_value_usd"] / df["revenue_usd"].where(df["revenue_usd"] > 0)
    return df


def get_risk_free_rate() -> float:
    """10-year US Treasury yield as a decimal (e.g. 0.0495 for 4.95%).

    Yahoo's ^TNX history() returns the yield directly in percentage points
    (e.g. 4.95 for 4.95%), so we only need to divide by 100 — verified against
    a live run where the raw close was 5.255, i.e. 5.255%, a plausible current
    10Y yield, not the ~0.5% you'd get from an incorrect extra /10.
    """
    closes = yf.Ticker("^TNX").history(period="5d")["Close"].dropna()
    if closes.empty:
        raise ValueError("Could not fetch ^TNX (10-year Treasury yield).")
    return float(closes.iloc[-1]) / 100


def peer_summary(df: pd.DataFrame, subject: str) -> pd.DataFrame:
    """Median/mean/min/max of key multiples across peers, excluding the subject company."""
    peers = df[df["ticker"] != subject]
    cols = ["trailing_pe", "forward_pe", "ev_to_ebitda", "ev_to_revenue"]
    return peers[cols].agg(["median", "mean", "min", "max"])


def export_to_excel(path: str, subject: CompanySnapshot, comps: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Write values (not formulas) to the two tabs. Requires openpyxl."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        subject.to_frame().to_excel(writer, sheet_name="Cover & Assumptions", index=False)
        comps.to_excel(writer, sheet_name="Trading Comps", index=False)
        summary.to_excel(writer, sheet_name="Trading Comps", startrow=len(comps) + 3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xlsx", metavar="PATH", help="also write the tabs to this Excel file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    snapshots = get_snapshots([DIAGEO_TICKER, *PEER_TICKERS])
    subject = snapshots.get(DIAGEO_TICKER)
    if subject is None:
        raise SystemExit(f"Could not fetch {DIAGEO_TICKER}; aborting.")

    print("=== DIAGEO ===")
    print(subject.to_frame().to_string(index=False))

    comps = add_usd_columns(snapshots_to_frame(snapshots))
    show = ["ticker", "name", "quote_currency", "price_usd", "market_cap_usd",
            "enterprise_value_usd", "ev_to_ebitda", "ev_to_revenue", "trailing_pe", "forward_pe", "beta"]
    print("\n=== PEER COMPS ===")
    print(comps[show].to_string(index=False))

    summary = peer_summary(comps, DIAGEO_TICKER)
    print("\n=== PEER SUMMARY (excl. Diageo) ===")
    print(summary.round(2).to_string())

    rf_rate = get_risk_free_rate()
    print(f"\n=== RISK-FREE RATE ===\n10-year US Treasury yield: {rf_rate:.4%}")

    if args.xlsx:
        export_to_excel(args.xlsx, subject, comps, summary)
        print(f"\nWrote {args.xlsx}")


if __name__ == "__main__":
    main()