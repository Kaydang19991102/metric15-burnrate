import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Metric 15: Overtime Burn Rate & Attrition", layout="wide")
st.title("📊 Metric 15: Overtime Burn Rate & Attrition Correlation")
st.write("Identifies departments and job roles with unsustainable workloads "
         "and models the financial cost of employee turnover.")

# --- REQUIRED COLUMNS ---
# These are the exact column names the uploaded CSV must contain
REQUIRED_COLUMNS = [
    "department", "job_role", "overtime", "attrition", "monthly_income"
]

# --- FORMULA CONSTANTS ---
# Weights for Burn Rate Index — must match Colab notebook exactly
W_OVERTIME  = 0.6   # Overtime is the primary driver of burnout
W_ATTRITION = 0.4   # Attrition is the downstream consequence

# Replacement cost multiplier tiers (SHRM industry standard)
MULT_LOW       = 0.5    # Annual salary < $40,000
MULT_MID       = 1.0    # Annual salary $40,000 – $79,999
MULT_HIGH      = 1.5    # Annual salary >= $80,000
LOW_THRESHOLD  = 40000
HIGH_THRESHOLD = 80000

# --- DATA LOADING ---
uploaded_file = st.file_uploader("Upload your HR dataset (CSV)", type="csv")

if uploaded_file is not None:

    # STUDENT NOTE: Load CSV into DataFrame
    df = pd.read_csv(uploaded_file)

    # STUDENT NOTE: Validate required columns before any computation
    # Prevents the app from crashing on unexpected files
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"❌ Missing required columns: {missing}. Please check your file.")
        st.stop()

    # STUDENT NOTE: Show first 10 rows so the user can verify the data loaded correctly
    st.subheader("Data Preview")
    st.dataframe(df.head(10))

    st.markdown("---")

    # --- INTERACTIVE FILTER ---
    # STUDENT NOTE: Department filter changes which rows enter the computation
    # Removing this widget would change every number in the output — it qualifies
    all_departments = sorted(df["department"].dropna().unique().tolist())
    selected_depts = st.multiselect(
        "Filter by Department",
        options=all_departments,
        default=all_departments,
        help="Select one or more departments to include in the analysis."
    )

    # STUDENT NOTE: Apply the department filter to the working DataFrame
    # All metric calculations below use df_filtered, not the full df
    df_filtered = df[df["department"].isin(selected_depts)].copy()

    if df_filtered.empty:
        st.warning("No data available for the selected departments.")
        st.stop()

    # --- METRIC COMPUTATION ---

    # STUDENT NOTE: Encode 'overtime' and 'attrition' as 0/1 flags
    # Mean of a 0/1 column equals the proportion of "Yes" in a group
    df_filtered["overtime_flag"]  = (df_filtered["overtime"]  == "Yes").astype(int)
    df_filtered["attrition_flag"] = (df_filtered["attrition"] == "Yes").astype(int)

    # STUDENT NOTE: Define grouping keys — analysis is per department + role combination
    GROUP_COLS = ["department", "job_role"]

    # STUDENT NOTE: Compute overtime rate per group (proportion working overtime)
    overtime_rate = (df_filtered.groupby(GROUP_COLS)["overtime_flag"]
                     .mean().rename("overtime_rate"))

    # STUDENT NOTE: Compute attrition rate per group (proportion who left)
    attrition_rate = (df_filtered.groupby(GROUP_COLS)["attrition_flag"]
                      .mean().rename("attrition_rate"))

    # STUDENT NOTE: Count total employees per group (for context and cost calculation)
    employee_count = (df_filtered.groupby(GROUP_COLS)["overtime_flag"]
                      .count().rename("employee_count"))

    # STUDENT NOTE: Count how many employees actually left (for cost exposure)
    attrited_count = (df_filtered.groupby(GROUP_COLS)["attrition_flag"]
                      .sum().rename("attrited_count"))

    # STUDENT NOTE: Compute average monthly income per group (base for cost multiplier)
    avg_monthly_income = (df_filtered.groupby(GROUP_COLS)["monthly_income"]
                          .mean().rename("avg_monthly_income"))

    # STUDENT NOTE: Combine all computed series into one results DataFrame
    results = pd.concat(
        [overtime_rate, attrition_rate, employee_count, attrited_count, avg_monthly_income],
        axis=1
    ).reset_index()

    # STUDENT NOTE: Compute Burn Rate Index — weighted sum of overtime and attrition rates
    # Formula must match the Colab notebook exactly (same weights)
    results["burn_rate_index"] = (
        (results["overtime_rate"]  * W_OVERTIME) +
        (results["attrition_rate"] * W_ATTRITION)
    ).round(4)

    # STUDENT NOTE: Compute average annual salary (monthly × 12)
    results["avg_annual_salary"] = results["avg_monthly_income"] * 12

    # STUDENT NOTE: Assign replacement cost multiplier based on salary tier
    def get_multiplier(annual_salary):
        # Entry-level: lower recruitment and onboarding cost
        if annual_salary < LOW_THRESHOLD:
            return MULT_LOW
        # Mid-level: moderate search and ramp-up cost
        elif annual_salary < HIGH_THRESHOLD:
            return MULT_MID
        # Senior/specialist: scarce supply and long ramp-up
        else:
            return MULT_HIGH

    results["replacement_multiplier"] = results["avg_annual_salary"].apply(get_multiplier)

    # STUDENT NOTE: Compute per-person replacement cost
    results["replacement_cost_per_person"] = (
        results["avg_annual_salary"] * results["replacement_multiplier"]
    ).round(2)

    # STUDENT NOTE: Compute total replacement cost exposure for the group
    # Number of leavers × cost to replace each one
    results["replacement_cost_exposure"] = (
        results["attrited_count"] * results["replacement_cost_per_person"]
    ).round(2)

    # STUDENT NOTE: Rename columns to plain English for display
    display_df = results.rename(columns={
        "department"                 : "Department",
        "job_role"                   : "Job Role",
        "overtime_rate"              : "Overtime Rate (%)",
        "attrition_rate"             : "Attrition Rate (%)",
        "employee_count"             : "Total Employees",
        "attrited_count"             : "Employees Who Left",
        "avg_annual_salary"          : "Avg Annual Salary ($)",
        "replacement_cost_per_person": "Replacement Cost Per Person ($)",
        "replacement_cost_exposure"  : "Total Replacement Cost Exposure ($)",
        "burn_rate_index"            : "Burn Rate Index"
    })

    # STUDENT NOTE: Convert rates to percentages for readability
    display_df["Overtime Rate (%)"]  = (display_df["Overtime Rate (%)"]  * 100).round(1)
    display_df["Attrition Rate (%)"] = (display_df["Attrition Rate (%)"] * 100).round(1)

    # STUDENT NOTE: Sort by Burn Rate Index descending — highest risk at top
    display_df = display_df.sort_values("Burn Rate Index", ascending=False).reset_index(drop=True)

    st.markdown("---")

    # --- HEADLINE METRICS ---
    # STUDENT NOTE: Show three KPI cards computed from the formula output
    col1, col2, col3 = st.columns(3)

    # Highest Burn Rate Index across all filtered groups
    top_bri     = display_df["Burn Rate Index"].max()
    top_role    = display_df.loc[display_df["Burn Rate Index"].idxmax(), "Job Role"]
    total_exposure = display_df["Total Replacement Cost Exposure ($)"].sum()
    avg_ot_rate = display_df["Overtime Rate (%)"].mean()

    col1.metric("🔥 Highest Burn Rate Index",
                f"{top_bri:.3f}",
                help=f"Role: {top_role}")
    col2.metric("💸 Total Replacement Cost Exposure",
                f"${total_exposure:,.0f}")
    col3.metric("⏱️ Avg Overtime Rate (filtered)",
                f"{avg_ot_rate:.1f}%")

    st.markdown("---")

    # --- RESULTS TABLE ---
    st.subheader("Full Results Table")
    st.dataframe(display_df, use_container_width=True)

    st.markdown("---")

    # --- CHARTS ---

    # STUDENT NOTE: Chart 1 — Burn Rate Index by Job Role (horizontal bar)
    st.subheader("Chart 1: Burn Rate Index by Job Role")
    fig1 = px.bar(
        display_df,
        x="Burn Rate Index",
        y="Job Role",
        color="Department",
        orientation="h",
        title="Burn Rate Index by Job Role",
        text="Burn Rate Index",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig1.update_layout(yaxis={"categoryorder": "total ascending"}, plot_bgcolor="white")
    fig1.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)

    # STUDENT NOTE: Chart 2 — Scatter: Overtime Rate vs Attrition Rate
    st.subheader("Chart 2: Overtime Rate vs Attrition Rate")
    fig2 = px.scatter(
        display_df,
        x="Overtime Rate (%)",
        y="Attrition Rate (%)",
        size="Total Employees",
        color="Department",
        hover_name="Job Role",
        text="Job Role",
        title="Overtime vs Attrition by Job Role",
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    # Reference lines at dataset averages
    fig2.add_vline(x=display_df["Overtime Rate (%)"].mean(),
                   line_dash="dash", line_color="grey")
    fig2.add_hline(y=display_df["Attrition Rate (%)"].mean(),
                   line_dash="dash", line_color="grey")
    fig2.update_traces(textposition="top center")
    fig2.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig2, use_container_width=True)

    # STUDENT NOTE: Chart 3 — Replacement Cost Exposure by Job Role
    st.subheader("Chart 3: Total Replacement Cost Exposure by Job Role")
    fig3 = px.bar(
        display_df.sort_values("Total Replacement Cost Exposure ($)", ascending=True),
        x="Total Replacement Cost Exposure ($)",
        y="Job Role",
        color="Department",
        orientation="h",
        title="Replacement Cost Exposure by Job Role",
        text="Total Replacement Cost Exposure ($)",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig3.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig3.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig3, use_container_width=True)

    # STUDENT NOTE: Chart 4 — Heatmap of Burn Rate Index by Department × Role
    st.subheader("Chart 4: Burn Rate Index Heatmap")
    pivot = display_df.pivot_table(
        index="Department", columns="Job Role",
        values="Burn Rate Index", aggfunc="mean"
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
        yaxis_title="Department"
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
        Costs are estimated at 50% of annual salary for entry-level roles, 100% for 
        mid-level, and 150% for senior/specialist roles, consistent with SHRM guidelines.
        """
    )

else:
    st.info("👆 Upload a CSV file to begin. Required columns: "
            f"{', '.join(REQUIRED_COLUMNS)}")
```

---

## `requirements.txt`
```
streamlit
pandas
plotly
kaleido
```

---

## Deployment Steps (10 minutes)
```
