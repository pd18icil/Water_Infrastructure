# 💧 Lebanon Water Infrastructure — Interactive Dashboard

An interactive Streamlit follow-up to the [Plotly visualization
assignment](../../1_Introduction/Practice%20on%20Visualizing%20with%20Python%20%26%20Plotly),
built on the same town-level water infrastructure dataset (Impact Open Data /
AUB Linked Data — 1,137 towns across 25 districts, 7 governorates).

**Live app:** https://water-infrastructure.streamlit.app/

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
- Two additional filters, each placed directly above the chart it affects: a
  minimum public-network-access slider above the bar/line charts on "Access &
  condition", and a "hide zero-point towns" toggle above the box chart on
  "Springs & water points". A town-name search box above the scatter chart
  highlights a matching point.
- A custom `.streamlit/config.toml` theme applies the same Berytus Red /
  black / gray palette used in the Plotly charts to every native widget
  (chips, sliders, checkboxes, active tab), so the whole app — not just the
  charts — matches the brand.

## Project structure

```
streamlit_app.py                        # the app (entry point for Streamlit Community Cloud)
requirements.txt                        # Python dependencies
.streamlit/config.toml                  # brand theme (Berytus Red palette)
139a27528eedba4a898bd7b623307805.csv    # source dataset
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
