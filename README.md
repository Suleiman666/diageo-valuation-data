# Diageo Valuation — DCF, Trading Comps & Precedent Transactions

A full equity research exercise on **Diageo plc (NYSE: DEO / LSE: DGE)**, built as a personal
project during placement-application preparation. It has three parts:

| File | What it is |
|---|---|
| **[`Diageo_Research_Note.pdf`](./Diageo_Research_Note.pdf)** | 2-page research note — the conclusion. View, valuation summary, key drivers, risks. **Start here.** |
| **[`Diageo_DCF_Comps_Precedent_Valuation.xlsx`](./Diageo_DCF_Comps_Precedent_Valuation.xlsx)** | The valuation model — DCF (Gordon Growth + exit multiple cross-check), WACC build-up, trading comps, precedent transactions, and a football field summary. Every figure in the note traces back to a formula in this workbook. |
| **[`pull_valuation_data.py`](./pull_valuation_data.py)** | A Python pipeline (`yfinance`, `pandas`) that pulls live market data for Diageo and four listed peers — price, shares outstanding, beta, debt, cash, EBITDA, revenue — and the 10-year US Treasury yield, with correct multi-currency handling (EUR/USD) and enterprise value computed from first principles rather than trusted from a vendor's precomputed field. |

## The headline

At $86.41 (11 Sep 2026), Diageo shares screen as **fairly valued to modestly undervalued**:
trading comps imply a fair value of $88.94 (+2.9%), the DCF base case implies $109.75 (+27%,
conditional on management's margin-recovery programme landing), and precedent M&A transactions
imply $57–$193 (median $138) — a much wider, control-premium-inflated range used here as
context rather than a primary valuation anchor. Full reasoning is in the research note.

## Why this exists

Most of the finance side of a placement application is built in Excel with numbers typed in by
hand. This project pairs that with a data-automation layer — showing both sides: the valuation
judgement (what a methodology is actually telling you, and when to trust one method over another)
and the engineering discipline to source the inputs correctly rather than trusting a vendor API
at face value.

## Three data bugs caught building this

Documented in full in the research note's Methodology section, and in more technical detail in
the Python script's comments:

1. **Yahoo Finance's precomputed enterprise value field overstated Diageo's EV by ~12x**
   ($886.6bn vs. an independently-computed ~$68bn) — fixed by computing EV from components
   (`market_cap + total_debt - total_cash`) rather than trusting the vendor's derived field.
2. **A defensive ADR-ratio sanity check was itself wrong** — it assumed Yahoo's `sharesOutstanding`
   for Diageo's ADR needed dividing by the 1:4 ADR ratio; testing against Yahoo's own market cap
   showed it didn't. The "fix" was solving a problem that didn't exist.
3. **The risk-free rate came out 10x too low** from an incorrect assumption about how Yahoo's
   `^TNX` ticker is quoted — caught because 0.53% is an implausible 10-year Treasury yield.

Each was only caught by cross-checking against an independently verifiable number — the
discipline the research note tries to apply throughout the valuation itself.

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