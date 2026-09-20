# 💧 Lebanon Water Infrastructure — Interactive Dashboard

An interactive Streamlit follow-up to the [Plotly visualization
assignment](../../1_Introduction/Practice%20on%20Visualizing%20with%20Python%20%26%20Plotly),
built on the same town-level water infrastructure dataset (Impact Open Data /
AUB Linked Data — 1,137 towns across 25 districts, 7 governorates).

**Live app:** _add the Streamlit Community Cloud link here after deploying_

## What it does

- Reuses four visualizations from Assignment 1 (bar, line, scatter, box —
  organized into two tabs) and applies the same district relabeling /
  data-cleaning work.
- Adds a **linked, drill-down filter pair** in the sidebar: choosing a
  **Governorate** narrows the **District** multiselect's options to just that
  governorate's districts, so the two widgets can't be set to a nonsensical
  combination.
- Surfaces two data-grounded insights (raw counts vs. normalized coverage;
  uneven reporting completeness) plus a live KPI row that reacts to the
  current filter.
- Includes a short design-justification write-up for each of the two linked
  filters, explaining the user question it answers, why that widget was
  chosen over an alternative, and which course concept it applies.

## Project structure

```
streamlit_app.py       # the app (entry point for Streamlit Community Cloud)
requirements.txt        # Python dependencies
139a27528eedba4a898bd7b623307805.csv   # source dataset
```

## Running it locally

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Data source

Impact Open Data, published via AUB's linked-data platform
(`linked.aub.edu.lb`). See the Assignment 1 notebook for the full cleaning
and analysis writeup, including how the `refArea` admin-level mismatch was
resolved.
