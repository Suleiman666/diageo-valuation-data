# Diageo Valuation — DCF, Trading Comps & Precedent Transactions

A full equity research exercise on **Diageo plc (NYSE: DEO / LSE: DGE)**, built as a personal
project during placement-application preparation. It has three parts:

| File | What it is |
|---|---|
| **[`Diageo_Research_Note.pdf`](./Diageo_Research_Note.pdf)** | 2-page research note — the conclusion. View, valuation summary, key drivers, risks. **Start here.** |
| **[`Diageo_DCF_Comps_Precedent_Valuation.xlsx`](./Diageo_DCF_Comps_Precedent_Valuation.xlsx)** | The valuation model — DCF (Gordon Growth + WACC/growth sensitivity grid), WACC build-up, trading comps, precedent transactions, and a football field summary. Every figure in the note traces back to a formula in this workbook. |
| **[`pull_valuation_data.py`](./pull_valuation_data.py)** | A Python pipeline (`yfinance`, `pandas`) that pulls live market data for Diageo and four listed peers — price, shares outstanding, beta, debt, cash, EBITDA, revenue — and the 10-year US Treasury yield, with correct multi-currency handling (EUR/USD) and enterprise value computed from first principles rather than trusted from a vendor's precomputed field. |

## The headline

At $85.34 (29 Sep 2026), against **FY2026A** financials (year ended 30 June 2026, published
6 Aug 2026), Diageo shares screen as **undervalued**: trading comps imply a median fair value of
$95.31 (+11.7%), the DCF base case implies $114.43 (+34%), and precedent M&A transactions imply
$62–$202 (median $146) — a much wider, control-premium-inflated range used here as context rather
than a primary valuation anchor. Full reasoning is in the research note.

## Why this exists

Most of the finance side of a placement application is built in Excel with numbers typed in by
hand. This project pairs that with a data-automation layer — showing both sides: the valuation
judgement (what a methodology is actually telling you, and when to trust one method over another)
and the engineering discipline to source the inputs correctly rather than trusting a vendor API
at face value.

## Four data-integrity issues caught building this

Documented in full in the research note's Methodology section:

1. **An earlier version of the model used stale financials.** It was built on Diageo's FY2025A
   results even though FY2026A results (published 6 Aug 2026) were already public before the
   note's original date. This wasn't caught by any automated check — it was flagged on review.
   It mattered: switching to the correct FY2026A base year moved the conclusion from roughly
   fairly-valued to clearly undervalued, because FY2026A's actual EBITDA and net debt are both
   more favourable than the earlier model's estimates, independent of any forecast assumption.
2. **Yahoo Finance's precomputed enterprise value field overstated Diageo's EV by ~12x**
   ($886.6bn vs. an independently-computed ~$68bn) — fixed by computing EV from components
   (`market_cap + total_debt - total_cash`) rather than trusting the vendor's derived field.
3. **A defensive ADR-ratio sanity check was itself wrong** — it assumed Yahoo's `sharesOutstanding`
   for Diageo's ADR needed dividing by the 1:4 ADR ratio; testing against Yahoo's own market cap
   showed it didn't. The "fix" was solving a problem that didn't exist.
4. **The risk-free rate came out 10x too low** from an incorrect assumption about how Yahoo's
   `^TNX` ticker is quoted — caught because 0.53% is an implausible 10-year Treasury yield.

The common thread across all four: check a number's currency, date, and provenance before
trusting it — not just whether the arithmetic built on top of it is internally consistent.

## Usage

```bash
pip install -r requirements.txt
python pull_valuation_data.py                    # print live data to console
python pull_valuation_data.py --xlsx out.xlsx     # also write to an Excel file
```

## Requirements

- Python 3.10+, internet access (queries Yahoo Finance live, no API key needed)
- Excel or Google Sheets to open the model

## Disclaimer

This is a personal, educational exercise using public information. It is not investment research
and not investment advice.

## License

MIT
