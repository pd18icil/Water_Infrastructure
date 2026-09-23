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

BRAND_FONT = dict(family="Proxima Nova, Arial, sans-serif", color=BLACK)
CHART_MARGIN = dict(t=20)

PUBLIC_NETWORK = "Potable water source - public network"
STATE_COLS = {
    "State of the water network - good": "Good",
    "State of the water network - acceptable": "Acceptable",
    "State of the water network - bad": "Bad",
}
CONDITIONS = ["Good", "Acceptable", "Bad"]
CONDITION_WEIGHTS = {c: f"{c} weight" for c in CONDITIONS + ["Unknown"]}
CONDITION_COLORS = {"Good": BLACK, "Acceptable": GRAY, "Bad": BERYTUS_RED, "Unknown": PALE_GRAY}
PERMANENT_SPRINGS = "Total number of permanent water springs"
SEASONAL_SPRINGS = "Total number of seasonal water springs"
SEASONAL_POINTS = "Total number of seasonal water points"

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

    # each town adds up to 1: a town flagging two states (2 say both Good and Bad) counts half in each
    flags = df[list(STATE_COLS)].rename(columns=STATE_COLS)
    n_flags = flags.sum(axis=1)
    weights = flags.div(n_flags.replace(0, np.nan), axis=0).fillna(0)
    weights["Unknown"] = (n_flags == 0).astype(float)
    for cond, col in CONDITION_WEIGHTS.items():
        df[col] = weights[cond]
    df["Condition"] = flags.apply(
        lambda row: " / ".join(c for c in CONDITIONS if row[c]) or "Unknown", axis=1
    )

    return df


def condition_counts(data: pd.DataFrame) -> pd.DataFrame:
    """Towns per district in each condition (Good/Acceptable/Bad/Unknown)."""
    return (
        data.groupby("District")[list(CONDITION_WEIGHTS.values())].sum()
        .rename(columns={col: cond for cond, col in CONDITION_WEIGHTS.items()})
    )


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


FILTER_DEFAULTS = {
    "gov_sel": [],
    "district_sel": [],
    "min_access": 0,
    "town_query": None,
    "hide_zero_points": False,
}


def _reset_filters():
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value


with st.sidebar:
    st.header("Filters")

    st.multiselect(
        "Governorate",
        ALL_GOVERNORATES,
        key="gov_sel",
        placeholder="All governorates",
        help="Leave empty to include all of Lebanon. Choosing governorates limits the "
             "District list below to their districts.",
    )

    gov_scope = st.session_state.gov_sel or ALL_GOVERNORATES
    districts_in_scope = sorted(df.loc[df["Governorate"].isin(gov_scope), "District"].unique())
    # drop districts left over from a previous governorate choice
    st.session_state.district_sel = [
        d for d in st.session_state.get("district_sel", []) if d in districts_in_scope
    ]

    st.multiselect(
        "District",
        districts_in_scope,
        key="district_sel",
        placeholder="All districts",
        help="Leave empty to include every district in scope. Options are limited to "
             "the governorate(s) selected above.",
    )

    filters_active = any(
        st.session_state.get(key, value) != value for key, value in FILTER_DEFAULTS.items()
    )
    st.button("Reset filters", on_click=_reset_filters, disabled=not filters_active)

selected_districts = st.session_state.district_sel or districts_in_scope
fdf = df[df["District"].isin(selected_districts)].copy()
is_filtered = len(fdf) < len(df)

# ============================================================
# Live KPI row — reacts to the current filter selection
# ============================================================


def summarize(data: pd.DataFrame) -> dict:
    reporting = len(data) - data[CONDITION_WEIGHTS["Unknown"]].sum()
    no_springs = (data[PERMANENT_SPRINGS] == 0) & (data[SEASONAL_SPRINGS] == 0)
    return {
        "access": data[PUBLIC_NETWORK].mean() * 100,
        "good": data[CONDITION_WEIGHTS["Good"]].sum() / reporting * 100 if reporting else np.nan,
        "unknown": data[CONDITION_WEIGHTS["Unknown"]].mean() * 100,
        "no_springs": no_springs.mean() * 100,
    }


current, national = summarize(fdf), summarize(df)


def kpi(label: str, key: str, help_text: str, higher_is_better: bool) -> None:
    value = current[key]
    delta = None
    if is_filtered and not np.isnan(value):
        delta = f"{value - national[key]:+.1f} pts vs. national"
    st.metric(
        label,
        "n/a" if np.isnan(value) else f"{value:.1f}%",
        delta=delta,
        delta_color="normal" if higher_is_better else "inverse",
        help=help_text,
        border=True,
    )


if is_filtered:
    govs = sorted(fdf["Governorate"].unique())
    n_districts = fdf["District"].nunique()
    st.caption(
        f"Showing {len(fdf):,} towns across {n_districts} "
        f"district{'s' if n_districts != 1 else ''} in {', '.join(govs)}"
    )
else:
    st.caption(f"Showing all {len(df):,} towns across {df['District'].nunique()} districts")

with st.container(horizontal=True):
    kpi("Public network access", "access",
        "Share of towns connected to the public water network.", True)
    kpi("Network in good condition", "good",
        "Among towns that report their network's condition, the share rated Good.", True)
    kpi("Condition unreported", "unknown",
        "Share of towns that report no network condition at all.", False)
    kpi("Towns with no springs", "no_springs",
        "Share of towns reporting zero permanent and zero seasonal springs.", False)

st.divider()

# ============================================================
# Chart builders (mirror Assignment 1's notebook logic)
# ============================================================


def make_bar_chart(data: pd.DataFrame) -> go.Figure:
    agg = (
        data.groupby("District")[PUBLIC_NETWORK]
        .agg(towns="count", with_access="sum")
        .assign(pct_with_access=lambda d: d["with_access"] / d["towns"] * 100)
        .sort_values("pct_with_access", ascending=False)
        .reset_index()
    )
    fig = px.bar(
        agg, x="pct_with_access", y="District", orientation="h",
        text=agg["pct_with_access"].round(1),
        labels={"pct_with_access": "% of towns with public network access"},
        color_discrete_sequence=[BERYTUS_RED],
    )
    fig.update_traces(texttemplate="%{text}%")
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(260, 34 * len(agg) + 80),
        font=BRAND_FONT, margin=CHART_MARGIN,
    )
    return fig


def make_condition_bar_chart(data: pd.DataFrame) -> go.Figure:
    categories = CONDITIONS + ["Unknown"]
    counts = condition_counts(data)[categories]
    shares = counts.div(counts.sum(axis=1), axis=0) * 100
    # horizontal bars draw bottom-up, so this puts the most complete reporting on top
    shares = shares.sort_values("Unknown", ascending=False)
    counts = counts.loc[shares.index]

    fig = go.Figure()
    for cond in categories:
        fig.add_trace(go.Bar(
            y=shares.index, x=shares[cond], name=cond, orientation="h",
            marker_color=CONDITION_COLORS[cond],
            text=[f"{v:.0f}%" if v >= 8 else "" for v in shares[cond]],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color=BLACK if cond == "Unknown" else "white"),
            customdata=counts[cond].round(),
            hovertemplate="<b>%{y}</b><br>" + cond + ": %{x:.1f}% (%{customdata:.0f} towns)<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=max(260, 30 * len(shares) + 110),
        font=BRAND_FONT, margin=dict(t=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, traceorder="normal"),
        xaxis=dict(title="% of all towns", range=[0, 100], ticksuffix="%"),
    )
    return fig


def national_profile() -> pd.Series:
    totals = condition_counts(df)[CONDITIONS].sum()
    return totals / totals.sum() * 100


def condition_profile(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Good/Acceptable/Bad shares among each district's reporting towns, and distance from national."""
    counts = condition_counts(data)[CONDITIONS]
    reporting = counts.sum(axis=1)
    counts, reporting = counts[reporting > 0], reporting[reporting > 0]
    shares = counts.div(reporting, axis=0) * 100
    deviation = (shares - national_profile()).abs().sum(axis=1) / 2
    return shares, reporting, deviation


def most_different(reporting: pd.Series, deviation: pd.Series) -> str:
    # ignore tiny samples (e.g. Tripoli: 3 reporting towns) unless nothing else qualifies
    eligible = deviation[reporting >= 10]
    return (eligible if not eligible.empty else deviation).idxmax()


def make_condition_profile_chart(data: pd.DataFrame) -> go.Figure:
    shares, reporting, deviation = condition_profile(data)
    most = most_different(reporting, deviation)
    label_all = len(shares) <= 5

    nat = national_profile()
    labels = []  # (end value, text, color)

    fig = go.Figure()
    # draw the emphasized district last so it sits on top of the gray lines
    for district in [d for d in shares.index if d != most] + [most]:
        emphasized = district == most
        if emphasized or label_all:
            labels.append((shares.loc[district, "Bad"], district, BLACK if emphasized else GRAY))
        fig.add_trace(go.Scatter(
            x=CONDITIONS, y=shares.loc[district], mode="lines+markers",
            line=dict(color=BLACK if emphasized else (GRAY if label_all else LIGHT_GRAY),
                      width=2.5 if emphasized else 1.5),
            marker=dict(size=6 if emphasized else 4),
            hovertemplate=f"<b>{district}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.add_trace(go.Scatter(
        x=CONDITIONS, y=nat, mode="lines+markers",
        line=dict(color=BERYTUS_RED, width=4), marker=dict(size=8),
        hovertemplate="<b>National average</b><br>%{x}: %{y:.1f}%<extra></extra>",
    ))
    labels.append((nat["Bad"], "National average", BERYTUS_RED))

    # nudge end labels apart so neighbouring lines don't hide each other's names
    min_gap = max(shares.to_numpy().max(), nat.max()) * 0.06
    placed = []
    for value, text, color in sorted(labels):
        y = value if not placed else max(value, placed[-1] + min_gap)
        placed.append(y)
        fig.add_annotation(
            x=2, y=y, text=text, showarrow=False, xanchor="left", xshift=10,
            font=dict(color=color, size=12),
        )

    fig.update_layout(
        height=420, font=BRAND_FONT, showlegend=False,
        margin=dict(t=20, r=140),
        xaxis=dict(range=[-0.15, 2.15]),
        yaxis=dict(title="% of towns that report a condition", ticksuffix="%", rangemode="tozero"),
    )
    return fig


def make_scatter_chart(data: pd.DataFrame, highlight_town: str | None = None) -> go.Figure:
    plot_df = data.copy()
    plot_df["Permanent springs (log1p)"] = np.log10(plot_df[PERMANENT_SPRINGS] + 1)
    plot_df["Seasonal springs (log1p)"] = np.log10(plot_df[SEASONAL_SPRINGS] + 1)

    tick_values = [0, 1, 2, 5, 10, 20, 50, 100, 200, 400]
    tick_positions = [np.log10(v + 1) for v in tick_values]

    fig = px.scatter(
        plot_df, x="Permanent springs (log1p)", y="Seasonal springs (log1p)",
        hover_name="Town",
        hover_data={
            "Permanent springs (log1p)": False, "Seasonal springs (log1p)": False,
            "District": True, PERMANENT_SPRINGS: True, SEASONAL_SPRINGS: True,
        },
        color_discrete_sequence=[BERYTUS_RED],
    )
    fig.update_traces(marker=dict(size=8, opacity=0.5, line=dict(width=0)))

    if highlight_town:
        match = plot_df[plot_df["Town"] == highlight_town]
        fig.add_trace(go.Scatter(
            x=match["Permanent springs (log1p)"], y=match["Seasonal springs (log1p)"],
            mode="markers+text", text=match["Town"], textposition="top center",
            textfont=dict(color=BLACK),
            marker=dict(size=18, symbol="circle-open", line=dict(width=3, color=BLACK)),
            hoverinfo="skip",
        ))

    fig.update_xaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values],
                     title="Permanent water springs")
    fig.update_yaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values],
                     title="Seasonal water springs")
    fig.update_layout(height=480, font=BRAND_FONT, margin=CHART_MARGIN, showlegend=False)
    return fig


def make_box_chart(data: pd.DataFrame) -> go.Figure:
    plot_df = data.copy()
    plot_df["Seasonal water points (log1p)"] = np.log10(plot_df[SEASONAL_POINTS] + 1)

    tick_values = [0, 1, 2, 5, 10, 20, 50, 100, 200]
    tick_positions = [np.log10(v + 1) for v in tick_values]

    fig = px.box(
        plot_df, x="District", y="Seasonal water points (log1p)",
        points="outliers",
        hover_data={"Seasonal water points (log1p)": False, SEASONAL_POINTS: True},
        color_discrete_sequence=[BERYTUS_RED],
    )
    fig.update_traces(marker=dict(color=BLACK, size=5), line=dict(color=BERYTUS_RED))
    fig.update_yaxes(tickvals=tick_positions, ticktext=[str(v) for v in tick_values], title="Seasonal water points")
    fig.update_layout(xaxis_tickangle=-30, height=420, font=BRAND_FONT, margin=CHART_MARGIN)
    return fig


# ============================================================
# Insights, computed from whatever is currently on screen
# ============================================================


def access_insight(data: pd.DataFrame) -> tuple[str, str]:
    agg = data.groupby("District")[PUBLIC_NETWORK].agg(towns="count", connected="sum")
    agg["pct"] = agg["connected"] / agg["towns"] * 100

    if len(agg) == 1:
        district, row = agg.index[0], agg.iloc[0]
        return (
            "How this district compares",
            f"{row.connected:.0f} of {row.towns:.0f} towns in {district} are connected to the "
            f"public network ({row.pct:.1f}%), against {national['access']:.1f}% nationally.",
        )

    top, bottom = agg["pct"].idxmax(), agg["pct"].idxmin()
    t, b = agg.loc[top], agg.loc[bottom]
    # among districts tied for the most connected towns, pick the least covered one
    most_connected = agg[agg["connected"] == agg["connected"].max()]["pct"].idxmin()
    m = agg.loc[most_connected]

    if most_connected != top:
        tie = f", tied with {top}" if m.connected == t.connected else ""
        return (
            "Raw counts mislead",
            f"{most_connected} has the most towns connected ({m.connected:.0f}{tie}), but with "
            f"{m.towns:.0f} towns in total that is only {m.pct:.1f}% coverage. {top} leads once "
            f"district size is accounted for, with {t.connected:.0f} of {t.towns:.0f} towns "
            f"({t.pct:.1f}%). Comparing districts of different sizes only works after dividing "
            "by each district's own total.",
        )
    return (
        "Coverage is uneven",
        f"{top} leads on both raw count and coverage, with {t.connected:.0f} of {t.towns:.0f} "
        f"towns connected ({t.pct:.1f}%). {bottom} trails at {b.pct:.1f}%, a gap of "
        f"{t.pct - b.pct:.1f} points.",
    )


def condition_insight(data: pd.DataFrame) -> tuple[str, str]:
    unknown = data.groupby("District")[CONDITION_WEIGHTS["Unknown"]].mean() * 100

    if len(unknown) == 1:
        return (
            "Part of the picture is missing",
            f"{unknown.iloc[0]:.0f}% of towns in {unknown.index[0]} don't report the condition of "
            f"their water network (national: {national['unknown']:.0f}%). The Good, Acceptable "
            "and Bad shares describe only the towns that do report.",
        )
    return (
        "Missing data isn't random",
        f"How completely a district reports its network condition varies from "
        f"{unknown.min():.0f}% missing ({unknown.idxmin()}) to {unknown.max():.0f}% missing "
        f"({unknown.idxmax()}). A district with mostly 'Unknown' towns isn't necessarily worse "
        "off; it may just be under-surveyed. Reading Good/Bad splits without checking the "
        "Unknown share risks mistaking a reporting gap for a real problem.",
    )


def profile_insight(data: pd.DataFrame) -> tuple[str, str]:
    shares, reporting, deviation = condition_profile(data)
    nat = national_profile()
    most = most_different(reporting, deviation)
    r, n = shares.loc[most], reporting[most]

    body = (
        f"Nationally, towns that report a condition split {nat['Good']:.0f}% Good, "
        f"{nat['Acceptable']:.0f}% Acceptable and {nat['Bad']:.0f}% Bad. "
    )
    if len(shares) == 1:
        title = "Against the national pattern"
        body += (
            f"In {most}, the split is {r['Good']:.0f}% Good, {r['Acceptable']:.0f}% Acceptable "
            f"and {r['Bad']:.0f}% Bad, based on {n:.0f} reporting towns."
        )
    else:
        title = f"{most} stands apart"
        body += (
            f"{most} differs most from that pattern, with {r['Good']:.0f}% Good and "
            f"{r['Bad']:.0f}% Bad across its {n:.0f} reporting towns."
        )
    if n < 15:
        body += " With so few reporting towns, a handful of answers can swing these shares."
    return title, body


def springs_insight(data: pd.DataFrame) -> tuple[str, str]:
    permanent, seasonal = data[PERMANENT_SPRINGS], data[SEASONAL_SPRINGS]
    total = permanent + seasonal
    if total.sum() == 0:
        return "No springs reported", "No town in the current selection reports any springs."

    top = data.loc[total.idxmax()]
    top_n = max(1, int(np.ceil(len(data) * 0.05)))
    top_share = total.nlargest(top_n).sum() / total.sum() * 100
    zero_share = (total == 0).mean() * 100

    sentences = []
    if len(data) >= 3 and permanent.std() > 0 and seasonal.std() > 0:
        r = permanent.corr(seasonal)
        strength = "strongly" if r >= 0.7 else "moderately" if r >= 0.4 else "weakly"
        sentences.append(
            f"Permanent and seasonal spring counts are {strength} correlated (r ≈ {r:.2f})."
        )
    holders = f"The top 5% of towns ({top_n}) hold" if top_n > 1 else "A single town holds"
    sentences.append(
        f"{holders} {top_share:.0f}% of all springs in view, led by {top.Town} "
        f"({top.District}) with {top[PERMANENT_SPRINGS]:.0f} permanent and "
        f"{top[SEASONAL_SPRINGS]:.0f} seasonal."
    )
    sentences.append(f"{zero_share:.0f}% of towns report no springs of either type.")

    title = "Springs are rare and lopsided" if zero_share >= 30 else "Springs are concentrated"
    return title, " ".join(sentences)


def water_points_insight(data: pd.DataFrame) -> tuple[str, str]:
    points = data[SEASONAL_POINTS]
    if points.sum() == 0:
        return "None reported", "No town in the current selection reports any seasonal water points."

    zero_share = (points == 0).mean() * 100
    medians = data.groupby("District")[SEASONAL_POINTS].median()
    if len(medians) == 1:
        median_text = f"the median town in {medians.index[0]} reports {medians.iloc[0]:.0f}"
    else:
        median_text = f"the median is 0 in {(medians == 0).sum()} of {len(medians)} districts"

    means = data.groupby("District")[SEASONAL_POINTS].mean()
    top = means.idxmax()
    district_towns = data[data["District"] == top]
    peak = district_towns.loc[district_towns[SEASONAL_POINTS].idxmax()]
    mean_without_peak = district_towns.drop(peak.name)[SEASONAL_POINTS].mean()

    body = (
        f"{zero_share:.0f}% of towns in view report zero seasonal water points, and {median_text}. "
    )
    lead = (
        f"{top}'s average is {means[top]:.2f} per town" if len(means) == 1
        else f"{top} has the highest average ({means[top]:.2f} per town)"
    )
    if len(district_towns) > 1 and mean_without_peak < means[top] * 0.6:
        title = "A handful of towns skew the averages"
        body += (
            f"{lead}, but that is driven by {peak.Town} reporting "
            f"{peak[SEASONAL_POINTS]:.0f}. Without it, {top}'s average falls to "
            f"{mean_without_peak:.2f}."
        )
    else:
        title = "Most towns report none"
        body += f"{lead}."
    return title, body


def chart_title(text: str, note: str | None = None) -> None:
    st.markdown(f"#### :red[{text}]")
    if note:
        st.caption(note)


def insight_card(title: str, body: str) -> None:
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
            min_value=0, max_value=100, step=5, key="min_access",
            help="Narrows the districts shown below to those with at least this much "
                 "public network access.",
        )
    access_by_district = fdf.groupby("District")[PUBLIC_NETWORK].mean() * 100
    eligible_districts = access_by_district[access_by_district >= min_access].index
    tab1_df = fdf[fdf["District"].isin(eligible_districts)]

    if tab1_df.empty:
        st.info(
            f"No district in the current selection reaches {min_access}% public network "
            "access. Lower the slider, or widen the region in the sidebar."
        )
    else:
        chart_title("% of towns with public network access")
        st.plotly_chart(make_bar_chart(tab1_df), width="stretch")
        insight_card(*access_insight(tab1_df))

        chart_title(
            "Water network condition by district",
            "Share of all towns in each district, sorted from most to least complete reporting.",
        )
        st.plotly_chart(make_condition_bar_chart(tab1_df), width="stretch")
        insight_card(*condition_insight(tab1_df))

        chart_title(
            "How each district's condition compares with the national average",
            "Each gray line is a district, based only on towns that report a condition; "
            "the black line is the one that differs most from the national average "
            "(among districts with at least 10 reporting towns).",
        )
        if (tab1_df["Condition"] == "Unknown").all():
            st.info("None of the towns in the current selection report their network condition.")
        else:
            st.plotly_chart(make_condition_profile_chart(tab1_df), width="stretch")
            insight_card(*profile_insight(tab1_df))

with tab2:
    town_options = sorted(fdf["Town"].unique())
    if st.session_state.get("town_query") not in town_options:
        st.session_state.town_query = None

    chart_title(
        "Permanent vs. seasonal water springs by town",
        "Log scale. Towns with zero springs sit at 0 on each axis.",
    )
    search_col, _ = st.columns([1, 2])
    with search_col:
        town_query = st.selectbox(
            "Highlight a town",
            options=town_options,
            index=None,
            key="town_query",
            placeholder="Start typing a town name…",
            help="Circles the selected town on the chart below.",
        )
    st.plotly_chart(make_scatter_chart(fdf, town_query), width="stretch")
    insight_card(*springs_insight(fdf))

    chart_title(
        "Distribution of seasonal water points by district",
        "Log scale. Dots are individual towns far above their district's typical value.",
    )
    hide_zero_points = st.checkbox(
        "Only show towns with at least one seasonal water point",
        key="hide_zero_points",
        help="Most towns report zero; this hides them to declutter the chart below.",
    )
    box_df = fdf
    if hide_zero_points:
        box_df = fdf[fdf[SEASONAL_POINTS] > 0]

    if box_df.empty:
        st.info("No towns in the current selection have any seasonal water points.")
    else:
        st.plotly_chart(make_box_chart(box_df), width="stretch")
        insight_card(*water_points_insight(fdf))

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
            "Condition",
            "Total number of permanent water springs",
            "Total number of seasonal water springs",
            "Total number of seasonal water points",
        ]].reset_index(drop=True),
        width="stretch",
    )
