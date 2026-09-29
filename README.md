# Diageo Valuation Data Puller

A Python script that pulls the live market data needed for a DCF / trading comps /
precedent transactions valuation model of **Diageo plc (NYSE: DEO)** — built as the
data-automation companion to a full Excel valuation model, as part of my prep for
finance placement applications (Lloyds Banking Group CIB Markets, SMBC).

It fetches, via [yfinance](https://github.com/ranaroussi/yfinance):
- Diageo's own price, shares outstanding, beta, debt, cash, EBITDA, and revenue
- The same for four listed peers — Pernod Ricard, Rémy Cointreau, Davide
  Campari-Milano, and Constellation Brands
- The 10-year US Treasury yield (risk-free rate, for the WACC build-up)

...and computes enterprise value and EV/EBITDA and EV/Revenue multiples for each,
correctly handling companies quoted in different currencies (EUR vs. USD).

## Why this exists

Most of the finance side of a placement application is built in Excel with numbers
typed in by hand. This script automates the data-gathering layer instead — the kind
of overlap between software engineering and finance that isn't common in either
direction.

## Usage

```bash
pip install -r requirements.txt
python pull_valuation_data.py                    # print to console
python pull_valuation_data.py --xlsx out.xlsx     # also write to an Excel file
```

## Three data-integrity bugs I caught building this

The most useful part of this project wasn't the happy path — it was three separate
cases where a data provider's number looked plausible but was wrong, and each one
only surfaced by cross-checking against an independently known value.

**1. Yahoo's `enterpriseValue` field was off by ~12x.**
Yahoo's precomputed EV for Diageo's ADR came back as **$886.6bn** — roughly the size
of a company twice as large as Apple, when Diageo's actual EV is around **$68-71bn**.
The fix: never trust a vendor's precomputed field for a derived figure — compute it
yourself from components you can verify individually (`market_cap + total_debt -
total_cash`), which landed within ~5% of the real, independently-sourced figure.

**2. A "defensive" ADR ratio check was actually introducing a false positive.**
I added a sanity check assuming Yahoo's `sharesOutstanding` for `DEO` was the
*ordinary share* count, requiring division by the 1:4 ADR ratio. Testing it against
Yahoo's own reported market cap showed `price × shares` (no ratio adjustment)
already matched to within 0.001% — Yahoo's `sharesOutstanding` for ADR tickers is
already ADR-share-equivalent. The "fix" I'd built was solving a problem that didn't
exist, and would have fired a false warning on every run.

**3. The risk-free rate came out 10x too low.**
I initially coded the well-known "CBOE `^TNX` quotes the yield ×10" convention
(historically true for some data feeds) — dividing Yahoo's raw value by an extra 10.
The result: a 10-year Treasury yield of 0.53%, obviously wrong. Testing against the
raw value showed `yfinance`'s `.history()` path returns the yield directly in
percentage points, not ×10. Removing the extra division gave ~5.25%, consistent with
where yields have actually been trading.

**The common thread:** every one of these looked fine until checked against an
independent number. None of the bugs were syntax errors — the code ran cleanly and
produced a plausible-looking result each time. That's the harder class of bug to
catch, and the reason every derived figure in this script is checked against
something verifiable rather than trusted on the strength of a "well-known" API
convention.

## Output

Two console tables (Diageo snapshot, peer comps with EV multiples) plus a peer
summary (median/mean/min/max), and the current risk-free rate. With `--xlsx`, the
same data is written to a `Cover & Assumptions` tab and a `Trading Comps` tab of an
Excel workbook.

## Requirements

- Python 3.10+
- Internet access (queries Yahoo Finance live — no API key needed)

## License

MIT
