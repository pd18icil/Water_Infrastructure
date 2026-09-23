import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# Brand palette (matches the AUB-branded deck from Assignment 1)
# ============================================================
BERYTUS_RED = "#840132"
BLACK = "#000000"
GRAY = "#808080"
LIGHT_GRAY = "#B3B3B3"
PALE_GRAY = "#D9D9D9"


def lerp_hex(c1, c2, t):
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


BRAND_FONT = dict(family="Proxima Nova, Arial, sans-serif", color=BLACK)
BRAND_TITLE_FONT = dict(family="Proxima Nova, Arial, sans-serif", color=BERYTUS_RED)

SYMBOLS = ["circle", "square", "diamond", "triangle-up", "x", "star", "triangle-down", "cross", "pentagon", "hexagon"]

st.set_page_config(
    page_title="Lebanon Water Infrastructure",
    layout="wide",
)

# ============================================================
# Data loading (cached; cheap filters happen outside this function)
# ============================================================
DATA_PATH = "139a27528eedba4a898bd7b623307805.csv"

RELABEL_TO_DISTRICT = {
    "Mount Lebanon Governorate": "Chouf District",
    "South Governorate": "Jezzine District",
    "Baalbek-Hermel Governorate": "Baalbek District",
    "Beqaa Governorate": "Rashaya District",
    "Nabatieh Governorate": "Nabatieh District",
    "North Governorate": "Koura District",
    "Akkar Governorate": "Akkar",
    "Tripoli District, Lebanon": "Tripoli District",
}

DISTRICT_TO_GOVERNORATE = {
    "Matn": "Mount Lebanon", "Byblos": "Mount Lebanon", "Baabda": "Mount Lebanon",
    "Aley": "Mount Lebanon", "Keserwan": "Mount Lebanon", "Chouf": "Mount Lebanon",
    "Hermel": "Baalbek-Hermel", "Baalbek": "Baalbek-Hermel",
    "Zahlé": "Beqaa", "Western Beqaa": "Beqaa", "Rashaya": "Beqaa",
    "Bint Jbeil": "Nabatieh", "Marjeyoun": "Nabatieh", "Hasbaya": "Nabatieh", "Nabatieh": "Nabatieh",
    "Zgharta": "North", "Bsharri": "North", "Batroun": "North", "Tripoli": "North",
    "Miniyeh–Danniyeh": "North", "Koura": "North",
    "Sidon": "South", "Tyre": "South", "Jezzine": "South",
    "Akkar": "Akkar",
}


def fix_mojibake(s):
    try:
        return s.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)

    df["District"] = df["refArea"].str.extract(r"/([^/]+)$")[0].str.replace("_", " ", regex=False)
    df["District"] = df["District"].apply(fix_mojibake)
    df["Town"] = df["Town"].apply(fix_mojibake)

    df["District"] = df["District"].replace(RELABEL_TO_DISTRICT)
    df["District"] = df["District"].str.replace(" District", "", regex=False)
    df["Governorate"] = df["District"].map(DISTRICT_TO_GOVERNORATE)

    return df


df = load_data()
ALL_GOVERNORATES = sorted(df["Governorate"].unique())

# ============================================================
# Header / context (Who / What framing)
# ============================================================
st.title("Lebanon Water Infrastructure")

with st.container(border=True):
    st.markdown(
        """
**Who is this for?** Anyone trying to understand where Lebanon's public water
network reaches best, and where it doesn't: a resident, a policy analyst, or
a student auditing the same dataset from the Plotly assignment.

**What should they walk away knowing?** That water infrastructure quality is
*uneven* across the country, that raw counts alone are misleading, and that
missing data is itself part of the story, not something to ignore.
"""
    )

st.divider()

# ============================================================
# Sidebar — the two REQUIRED linked interaction features
# ============================================================


def _on_governorate_change():
    scope = sorted(df.loc[df["Governorate"].isin(st.session_state.gov_sel), "District"].unique())
    st.session_state.district_sel = scope


with st.sidebar:
    st.header("Filters")

    st.multiselect(
        "Governorate",
        ALL_GOVERNORATES,
        default=ALL_GOVERNORATES,
        key="gov_sel",
        on_change=_on_governorate_change,
        help="Sets the region in scope. Changing this resets the District list below to match.",
    )

    districts_in_scope = sorted(df.loc[df["Governorate"].isin(st.session_state.gov_sel), "District"].unique())
    st.session_state.setdefault("district_sel", districts_in_scope)
    # keep any stale selections from a prior (wider) governorate scope out of the widget
    st.session_state.district_sel = [d for d in st.session_state.district_sel if d in districts_in_scope]

    st.multiselect(
        "District",
        districts_in_scope,
        key="district_sel",
        help="Options are limited to districts inside the governorate(s) selected above.",
    )

selected_districts = st.session_state.district_sel

if not selected_districts:
    st.warning("Select at least one district in the sidebar to see the charts.")
    st.stop()

fdf = df[df["District"].isin(selected_districts)].copy()

# ============================================================
# Live KPI row — reacts to the current filter selection
# ============================================================
pct_access_current = fdf["Potable water source - public network"].mean() * 100

with st.container(horizontal=True):
    st.metric("Towns in view", f"{len(fdf):,}", border=True)
    st.metric("Districts in view", fdf["District"].nunique(), border=True)
    st.metric("Governorates in view", fdf["Governorate"].nunique(), border=True)
    st.metric("Avg. public network access", f"{pct_access_current:.1f}%", border=True)

st.divider()

# ============================================================
# Chart builders (mirror Assignment 1's notebook logic)
# ============================================================


def make_bar_chart(data: pd.DataFrame) -> go.Figure:
    agg = (
        data.groupby("District")["Potable water source - public network"]
        .agg(towns="count", with_access="sum")
        .assign(pct_with_access=lambda d: d["with_access"] / d["towns"] * 100)
        .sort_values("pct_with_access", ascending=False)
        .reset_index()
    )
    fig = px.bar(
        agg, x="pct_with_access", y="District", orientation="h",
        title="% of towns with public network access",
        text=agg["pct_with_access"].round(1),
        labels={"pct_with_access": "% of towns with public network access"},
        color_discrete_sequence=[BERYTUS_RED],
    )
    fig.update_traces(texttemplate="%{text}%")
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(320, 34 * len(agg) + 120),
        font=BRAND_FONT, title_font=BRAND_TITLE_FONT,
    )
    return fig


def make_line_chart(data: pd.DataFrame) -> go.Figure:
    state_cols = {
        "State of the water network - good": "Good",
        "State of the water network - acceptable": "Acceptable",
        "State of the water network - bad": "Bad",
    }
    known = data[list(state_cols)].sum(axis=1) >= 1
    known_count = known.groupby(data["District"]).sum()
    total_count = data.groupby("District").size()

    share = data.groupby("District")[list(state_cols)].sum().rename(columns=state_cols)
    share = share.div(known_count.replace(0, np.nan), axis=0) * 100
    share["Unknown (% of all towns)"] = (1 - known_count / total_count) * 100
    share = share.sort_values("Good", ascending=False).reset_index()

    fig = px.line(
        share, x="District", y=["Good", "Acceptable", "Bad", "Unknown (% of all towns)"],
        markers=True,
        title="Water network condition (Good/Acceptable/Bad: % of towns with a known state)",
        labels={"value": "%", "variable": "Network state"},
        color_discrete_map={
            "Good": BLACK, "Acceptable": GRAY, "Bad": BERYTUS_RED,
            "Unknown (% of all towns)": LIGHT_GRAY,
        },
    )
    fig.for_each_trace(
        lambda t: t.update(line=dict(dash="dash")) if t.name == "Unknown (% of all towns)" else None
    )
    fig.update_layout(
        xaxis_tickangle=-45, height=460,
        font=BRAND_FONT, title_font=BRAND_TITLE_FONT,
    )
    return fig


def make_scatter_chart(data: pd.DataFrame, highlight_query: str = "") -> go.Figure:
    districts = sorted(data["District"].unique())
    palette = [lerp_hex(BERYTUS_RED, GRAY, i / max(1, len(districts) - 1)) for i in range(len(districts))]
    color_map = dict(zip(districts, palette))
    symbol_map = {d: SYMBOLS[i % len(SYMBOLS)] for i, d in enumerate(districts)}

    plot_df = data.copy()
    plot_df["Permanent springs (log1p)"] = np.log10(plot_df["Total number of permanent water springs"] + 1)
    plot_df["Seasonal springs (log1p)"] = np.log10(plot_df["Total number of seasonal water springs"] + 1)

    tick_values = [0, 1, 2, 5, 10, 20, 50, 100, 200, 400]
    tick_positions = [np.log10(v + 1) for v in tick_values]

    fig = px.scatter(
        plot_df, x="Permanent springs (log1p)", y="Seasonal springs (log1p)",
        color="District", symbol="District", hover_name="Town",
        hover_data={
            "Permanent springs (log1p)": False, "Seasonal springs (log1p)": False,
            "Total number of permanent water springs": True,
            "Total number of seasonal water springs": True,
        },
        title="Permanent vs. seasonal water springs by town (log scale, all towns incl. zeros)",
        color_discrete_map=color_map, symbol_map=symbol_map,
    )
    fig.update_traces(marker=dict(size=8, opacity=0.75, line=dict(width=0)))

    if highlight_query.strip():
        matches = plot_df[plot_df["Town"] == highlight_query.strip()]
        if not matches.empty:
            fig.add_trace(go.Scatter(
                x=matches["Permanent springs (log1p)"], y=matches["Seasonal springs (log1p)"],
                mode="markers+text", text=matches["Town"], textposition="top center",
                marker=dict(size=16, color=BERYTUS_RED, symbol="circle-open", line=dict(width=3, color=BERYTUS_RED)),
                name=f"Match: {highlight_query}", showlegend=True,
            ))

    fig.update_xaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values],
                      title="Total number of permanent water springs")
    fig.update_yaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values],
                      title="Total number of seasonal water springs")
    fig.update_layout(height=520, font=BRAND_FONT, title_font=BRAND_TITLE_FONT)
    return fig, matches if highlight_query.strip() else None


def make_box_chart(data: pd.DataFrame) -> go.Figure:
    plot_df = data.copy()
    plot_df["Seasonal water points (log1p)"] = np.log10(plot_df["Total number of seasonal water points"] + 1)

    tick_values = [0, 1, 2, 5, 10, 20, 50, 100, 200]
    tick_positions = [np.log10(v + 1) for v in tick_values]

    fig = px.box(
        plot_df, x="District", y="Seasonal water points (log1p)",
        title="Distribution of seasonal water points by district",
        points="outliers",
        hover_data={"Seasonal water points (log1p)": False, "Total number of seasonal water points": True},
        color_discrete_sequence=[BERYTUS_RED],
    )
    fig.update_traces(marker=dict(color=BLACK, size=5), line=dict(color=BERYTUS_RED))
    fig.update_yaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values], title="Seasonal water points")
    fig.update_layout(xaxis_tickangle=-30, height=460, font=BRAND_FONT, title_font=BRAND_TITLE_FONT)
    return fig


def insight_card(title: str, body: str) -> None:
    """A finding grounded in the full dataset, shown directly under the chart it explains."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(body)


# ============================================================
# Charts, organized into tabs (keeps either pair in focus, not all 4 at once)
# Each tab also has its own filter, scoped to the fields it displays.
# ============================================================
tab1, tab2 = st.tabs(["Access & condition", "Springs & water points"])

with tab1:
    filter_col, _ = st.columns([1, 2])
    with filter_col:
        min_access = st.slider(
            "Minimum public network access (%)",
            min_value=0, max_value=100, value=0, step=5, key="min_access",
            help="Narrows the districts shown below to those with at least this much "
                 "public network access.",
        )
    access_by_district = fdf.groupby("District")["Potable water source - public network"].mean() * 100
    eligible_districts = access_by_district[access_by_district >= min_access].index
    tab1_df = fdf[fdf["District"].isin(eligible_districts)]

    if tab1_df.empty:
        st.info("No districts in the current selection meet that access threshold.")
    else:
        st.plotly_chart(make_bar_chart(tab1_df), width="stretch")
        insight_card(
            "Raw counts mislead",
            "Akkar looks like a co-leader in public network access, tied with Matn at 56 "
            "towns connected. But Akkar has 144 towns total, so that's only 38.9% coverage, "
            "below the district median. Matn's 56 towns out of 72 means 77.8% coverage, the "
            "real leader. Comparing districts of very different sizes only works once you "
            "divide by each district's own total.",
        )

        st.plotly_chart(make_line_chart(tab1_df), width="stretch")
        insight_card(
            "Missing data isn't random",
            "How completely a district reports its network condition varies from 22% missing "
            "(Matn) to 71% missing (Rashaya). A district with mostly 'Unknown' towns isn't "
            "necessarily worse off; it may just be under-surveyed. Reading Good/Bad splits "
            "without checking the Unknown share risks mistaking a reporting gap for a real "
            "problem.",
        )

with tab2:
    town_options = sorted(fdf["Town"].unique())
    if st.session_state.get("town_query") not in town_options:
        st.session_state.town_query = None

    search_col, _ = st.columns([1, 2])
    with search_col:
        town_query = st.selectbox(
            "Highlight a town",
            options=town_options,
            index=None,
            key="town_query",
            placeholder="Start typing a town name…",
            help="Highlights the selected town on the scatter chart below.",
        ) or ""
    scatter_fig, town_matches = make_scatter_chart(fdf, town_query)
    st.plotly_chart(scatter_fig, width="stretch")
    insight_card(
        "Springs are rare and lopsided",
        "Permanent and seasonal spring counts are only moderately correlated (r ≈ 0.54), "
        "and a handful of towns account for nearly all of the extremes: Rahbeh (Akkar) "
        "reports 100 permanent and 365 seasonal springs, Aammatour (Chouf) reports 115 and "
        "250, and Mayrouba (Keserwan) has the highest permanent count of any town (150). "
        "Meanwhile, 55% of all towns report zero springs of either type.",
    )

    hide_zero_points = st.checkbox(
        "Only show towns with at least one seasonal water point",
        key="hide_zero_points",
        help="72% of towns report zero; this hides them to declutter the chart below.",
    )
    box_df = fdf
    if hide_zero_points:
        box_df = fdf[fdf["Total number of seasonal water points"] > 0]

    if box_df.empty:
        st.info("No towns in the current selection have any seasonal water points.")
    else:
        st.plotly_chart(make_box_chart(box_df), width="stretch")
        insight_card(
            "A handful of towns skew every district",
            "72% of all towns report zero seasonal water points, and the median is 0 in "
            "every one of the top districts by town count. Akkar's mean (1.94) looks "
            "meaningfully higher than its neighbors, but that's driven by a single outlier "
            "town reporting 200, not a district-wide pattern.",
        )

st.divider()

# ============================================================
# Design justification — the two REQUIRED linked filters
# ============================================================
st.subheader("Design justification")

with st.expander("Why a Governorate filter?"):
    st.markdown(
        """
**User question it answers:** *"Which region of Lebanon should I look at first?"*

**Why this widget:** A `st.multiselect` scopes the page to one or more governorates
before any district-level detail appears. An `st.pills`/`st.segmented_control`
(all options visible at once) was considered, since those read faster for small
sets. But with 7 governorates feeding into up to 25 downstream districts, a
dropdown-based multiselect scales better and keeps the sidebar compact.

**Course concept:** This is the *Who/What* framing from class, applied to data
instead of an audience: *"the more you narrow down your target [scope], the
better chance you have at successful communication."* Presenting all 25
districts immediately would be exactly the kind of clutter the course warns
against; this filter removes it before the reader even sees a chart.
"""
    )

with st.expander("Why a District filter?"):
    st.markdown(
        """
**User question it answers:** *"Within the region I picked, which specific
districts do I want to compare?"*

**Why this widget:** This `st.multiselect`'s **options are computed from the
Governorate selection**, not fixed: picking "Mount Lebanon" narrows the list
from 25 districts to 6. An independent second filter was considered and
rejected, since it would let a reader combine, say, Beqaa Governorate with
Matn District (which isn't even in Beqaa), a nonsensical selection the linked
design makes structurally impossible.

**Course concept:** This is *focusing attention*: the widget only ever shows
options relevant to the current context, so the reader compares real
alternatives instead of scanning a flat list of 25 checkboxes. It's also the
drill-down mechanic itself. Governorate sets the scope, District lets the
reader go one level deeper *inside* that scope, rather than filtering
independently.
"""
    )

st.divider()

with st.expander("Show underlying data for the current selection"):
    st.dataframe(
        fdf[[
            "Town", "District", "Governorate",
            "Potable water source - public network",
            "State of the water network - good",
            "State of the water network - acceptable",
            "State of the water network - bad",
            "Total number of permanent water springs",
            "Total number of seasonal water springs",
            "Total number of seasonal water points",
        ]].reset_index(drop=True),
        width="stretch",
    )
