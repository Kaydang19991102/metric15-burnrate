import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Metric 15: Overtime Burn Rate & Attrition", layout="wide")
st.title("📊 Metric 15: Overtime Burn Rate & Attrition Correlation")
st.write(
    "Identifies departments and job roles with unsustainable workloads "
    "and models the financial cost of employee turnover."
)

# --- SIDEBAR: HOW TO USE + REQUIRED COLUMNS ---
with st.sidebar:
    st.markdown("### How to use")
    st.markdown(
        """
        1. Upload the processed metrics CSV
        2. Use the filters to focus the analysis
        3. Read the interpretation panels
        4. Use the results table to plan HR interventions
        """
    )
    st.markdown("---")
    st.markdown("### Required columns")
    required_display = [
        "department",
        "job_role",
        "Total Employees",
        "Overtime Count",
        "Attrition Count",
        "Monthly Income",
        "Overtime Rate",
        "Attrition Rate",
        "Burn Rate Index",
        "Average Annual Salary",
        "Replacement Multiplier",
        "Replacement Cost",
        "Replacement Cost Exposure",
    ]
    for col in required_display:
        st.markdown(
            f"- <code style='background-color:#1e3a2f; color:#4ade80; "
            f"padding:2px 6px; border-radius:4px;'>{col}</code>",
            unsafe_allow_html=True
        )

# --- REQUIRED COLUMNS ---
# These match the pre-aggregated CSV exported from the Colab notebook
REQUIRED_COLUMNS = [
    "department",
    "job_role",
    "Overtime Rate",
    "Attrition Rate",
    "Total Employees",
    "Attrition Count",
    "Burn Rate Index",
    "Replacement Cost Exposure",
    "Average Annual Salary",
]

# --- DATA LOADING ---
uploaded_file = st.file_uploader("Upload your processed HR metrics CSV", type="csv")

if uploaded_file is not None:

    # STUDENT NOTE: Load the CSV into a DataFrame
    df = pd.read_csv(uploaded_file)

    # STUDENT NOTE: Strip whitespace from column names to avoid hidden space bugs
    # The exported CSV had a trailing space in "Overtime " — this catches it automatically
    df.columns = df.columns.str.strip()

    # STUDENT NOTE: Validate that all required columns are present before proceeding
    # Prevents the app from crashing on unexpected or wrong files
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"❌ Missing required columns: {missing}. Please check your file.")
        st.expander("📋 Columns found in your file").write(df.columns.tolist())
        st.stop()

    # STUDENT NOTE: Show the first 10 rows so the user can verify data loaded correctly
    st.subheader("Data Preview")
    st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")

    # --- INTERACTIVE FILTER ---
    # STUDENT NOTE: Department multiselect filter — changes which rows enter ALL
    # computations below. Removing this widget would change every headline number.
    all_departments = sorted(df["department"].dropna().unique().tolist())
    selected_depts = st.multiselect(
        "🔎 Filter by Department",
        options=all_departments,
        default=all_departments,
        help="Select one or more departments to include in the analysis."
    )

    # STUDENT NOTE: Apply the filter — all metric calculations use df_f, not full df
    df_f = df[df["department"].isin(selected_depts)].copy()

    if df_f.empty:
        st.warning("No data available for the selected departments.")
        st.stop()

    # --- METRIC COMPUTATION ---
    # STUDENT NOTE: Convert rates to percentages for display
    # Raw values are proportions (0–1); multiplying by 100 gives readable percentages
    df_f["Overtime Rate (%)"]  = (df_f["Overtime Rate"]  * 100).round(1)
    df_f["Attrition Rate (%)"] = (df_f["Attrition Rate"] * 100).round(1)

    # STUDENT NOTE: Sort by Burn Rate Index descending — highest risk at top
    df_f = df_f.sort_values("Burn Rate Index", ascending=False).reset_index(drop=True)

    # STUDENT NOTE: Compute headline KPI values from the formula output columns
    # These are derived from the data — not hardcoded
    top_bri          = df_f["Burn Rate Index"].max()
    top_role         = df_f.loc[df_f["Burn Rate Index"].idxmax(), "job_role"]
    total_exposure   = df_f["Replacement Cost Exposure"].sum()
    avg_ot_rate      = df_f["Overtime Rate (%)"].mean()

    # --- HEADLINE METRICS ---
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)

    # STUDENT NOTE: st.metric() displays computed values in KPI card format
    col1.metric(
        "🔥 Highest Burn Rate Index",
        f"{top_bri:.3f}",
        help=f"Role with highest BRI: {top_role}"
    )
    col2.metric(
        "💸 Total Replacement Cost Exposure",
        f"${total_exposure:,.0f}"
    )
    col3.metric(
        "⏱️ Avg Overtime Rate (filtered)",
        f"{avg_ot_rate:.1f}%"
    )

    st.markdown("---")

    # --- RESULTS TABLE ---
    st.subheader("Full Results Table")

    # STUDENT NOTE: Rename columns to plain English for non-technical display
    display_df = df_f.rename(columns={
        "department"               : "Department",
        "job_role"                 : "Job Role",
        "Total Employees"          : "Total Employees",
        "Attrition Count"          : "Employees Who Left",
        "Average Annual Salary"    : "Avg Annual Salary ($)",
        "Replacement Cost Exposure": "Total Replacement Cost Exposure ($)",
        "Burn Rate Index"          : "Burn Rate Index",
    })

    st.dataframe(display_df, use_container_width=True)

    st.markdown("---")

    # --- CHARTS ---

    # STUDENT NOTE: Chart 1 — Burn Rate Index by Job Role (horizontal bar)
    # Horizontal layout prevents label overlap for long role names
    st.subheader("Chart 1: Burn Rate Index by Job Role")
    fig1 = px.bar(
        df_f,
        x="Burn Rate Index",
        y="job_role",
        color="department",
        orientation="h",
        title="Burn Rate Index by Job Role",
        labels={"Burn Rate Index": "Burn Rate Index (0–1)", "job_role": ""},
        text="Burn Rate Index",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig1.update_layout(
        yaxis={"categoryorder": "total ascending"},
        plot_bgcolor="white",
        height=450
    )
    fig1.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)

    # STUDENT NOTE: Chart 2 — Scatter: Overtime Rate vs Attrition Rate
    # Bubble size = total employees; upper-right quadrant = highest risk
    st.subheader("Chart 2: Overtime Rate vs Attrition Rate")
    fig2 = px.scatter(
        df_f,
        x="Overtime Rate (%)",
        y="Attrition Rate (%)",
        size="Total Employees",
        color="department",
        hover_name="job_role",
        text="job_role",
        title="Overtime vs Attrition by Job Role",
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    # STUDENT NOTE: Reference lines at dataset averages to mark above/below average zones
    fig2.add_vline(
        x=df_f["Overtime Rate (%)"].mean(),
        line_dash="dash", line_color="grey",
        annotation_text="Avg OT"
    )
    fig2.add_hline(
        y=df_f["Attrition Rate (%)"].mean(),
        line_dash="dash", line_color="grey",
        annotation_text="Avg Attrition"
    )
    fig2.update_traces(textposition="top center")
    fig2.update_layout(plot_bgcolor="white", height=500)
    st.plotly_chart(fig2, use_container_width=True)

    # STUDENT NOTE: Chart 3 — Replacement Cost Exposure by Job Role
    # Sorted ascending so the most expensive role appears at the top of horizontal bars
    st.subheader("Chart 3: Total Replacement Cost Exposure by Job Role")
    fig3 = px.bar(
        df_f.sort_values("Replacement Cost Exposure", ascending=True),
        x="Replacement Cost Exposure",
        y="job_role",
        color="department",
        orientation="h",
        title="Replacement Cost Exposure by Job Role",
        labels={"Replacement Cost Exposure": "Replacement Cost ($)", "job_role": ""},
        text="Replacement Cost Exposure",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig3.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig3.update_layout(plot_bgcolor="white", height=450)
    st.plotly_chart(fig3, use_container_width=True)

    # STUDENT NOTE: Chart 4 — Heatmap of Burn Rate Index by Department × Role
    # Red = high burn rate (dangerous), Green = low (stable)
    st.subheader("Chart 4: Burn Rate Index Heatmap")
    pivot = df_f.pivot_table(
        index="department",
        columns="job_role",
        values="Burn Rate Index",
        aggfunc="mean"
    )
    fig4 = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="RdYlGn_r",
        text=pivot.values.round(3),
        texttemplate="%{text}",
        colorbar=dict(title="Burn Rate Index")
    ))
    fig4.update_layout(
        title="Burn Rate Index: Department × Job Role",
        xaxis_title="Job Role",
        yaxis_title="Department",
        height=400
    )
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # --- INTERPRETATION PANEL ---
    st.subheader("📌 How to Read This Report")
    st.info(
        """
        **What the Burn Rate Index measures:**
        The Burn Rate Index (BRI) combines two signals — the percentage of employees
        working overtime (weighted 60%) and the percentage who have left the company
        (weighted 40%). A higher index means a role is simultaneously overworked and
        losing people, which is the most dangerous combination for business continuity.

        **What to pay attention to:**
        - Any role with a BRI above 0.40 should be flagged for immediate HR review.
        - The scatter chart (Chart 2) reveals whether overtime and attrition move together
          in your organisation — roles in the upper-right quadrant are the highest priority.
        - The Replacement Cost Exposure (Chart 3) converts the human problem into a
          financial one. Use this to make the business case for intervention.
        - The heatmap (Chart 4) shows which department-role combinations are systemic
          problems versus isolated cases.

        **Replacement cost methodology:**
        Costs are estimated at 50% of annual salary for entry-level roles (<$40k),
        100% for mid-level ($40k–$80k), and 150% for senior/specialist roles (>$80k),
        consistent with SHRM guidelines.
        """
    )

else:
    st.info(
        "👆 Upload the **metric15_burn_rate_results.csv** file exported from your "
        "Colab notebook to begin.\n\n"
        f"**Required columns:** {', '.join(REQUIRED_COLUMNS)}"
    )
