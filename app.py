import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd
import glob
import os

st.set_page_config(layout="wide", page_title="Health & Retirement Study Explorer")

DATA_DIR = "randhrs_parquet"

WAVE_INFO = {
    "r1":  ("Wave 1 (1992)", 1992),
    "r2":  ("Wave 2 (1994)", 1994),
    "r3":  ("Wave 3 (1996)", 1996),
    "r4":  ("Wave 4 (1998)", 1998),
    "r5":  ("Wave 5 (2000)", 2000),
    "r6":  ("Wave 6 (2002)", 2002),
    "r7":  ("Wave 7 (2004)", 2004),
    "r8":  ("Wave 8 (2006)", 2006),
    "r9":  ("Wave 9 (2008)", 2008),
    "r10": ("Wave 10 (2010)", 2010),
    "r11": ("Wave 11 (2012)", 2012),
    "r12": ("Wave 12 (2014)", 2014),
    "r13": ("Wave 13 (2016)", 2016),
    "r14": ("Wave 14 (2018)", 2018),
    "r15": ("Wave 15 (2020)", 2020),
    "r16": ("Wave 16 (2022)", 2022)
}

# Plain-English curated metrics directly from RAND handbook conceptual sections
MEASURES_CATALOG = {
    "Chronic Health Conditions": {
        "hibpe":  ("High Blood Pressure / Hypertension (Doctor Diagnosed)", "binary", "0 = No, 1 = Yes"),
        "hibpe2": ("High Blood Pressure (Doctor Diagnosed or Taking Meds)", "binary", "0 = No, 1 = Yes"),
        "diabe":  ("Diabetes (Doctor Diagnosed)", "binary", "0 = No, 1 = Yes"),
        "diabe2": ("Diabetes (Doctor Diagnosed or on Insulin/Pills)", "binary", "0 = No, 1 = Yes"),
        "hearte": ("Heart Disease or Heart Attack (Ever Diagnosed)", "binary", "0 = No, 1 = Yes"),
        "stroke": ("Stroke (Doctor Diagnosed)", "binary", "0 = No, 1 = Yes"),
        "cancre": ("Cancer (Any type except skin cancer)", "binary", "0 = No, 1 = Yes"),
        "lunge":  ("Chronic Lung Disease (COPD, Chronic Bronchitis, Asthma)", "binary", "0 = No, 1 = Yes"),
        "arthre": ("Arthritis or Rheumatism", "binary", "0 = No, 1 = Yes"),
        "shlt":   ("General Health Rating", "scale", "1 = Excellent, 2 = Very Good, 3 = Good, 4 = Fair, 5 = Poor"),
    },
    "Memory & Cognitive Function": {
        "imtot":    ("Immediate Word Recall (Memory test: recall words right away)", "score", "Points: 0 to 10 (Higher = Better memory)"),
        "dltot":    ("Delayed Word Recall (Memory test: recall words after delay)", "score", "Points: 0 to 10 (Higher = Better memory)"),
        "ser7":     ("Serial 7s Test (Working memory: count backwards by 7 from 100)", "score", "Points: 0 to 5 (Higher = Better focus)"),
        "cogtot":   ("Composite Cognitive Battery (Full mental status score)", "score", "Points: 0 to 35 (Higher = Intact cognition)"),
        "cogtot27": ("Cognitive Summary Index (27-point battery)", "score", "Points: 0 to 27 (Scores under 7 indicate severe impairment)"),
    },
    "Mental Health & Well-Being": {
        "cesd":    ("CES-D Depression Score (Sum of depressive symptoms)", "score", "Score: 0 to 8 (Scores >= 3 suggest clinically meaningful distress)"),
        "smokev":  ("Ever Smoked Cigarettes Regularly", "binary", "0 = No, 1 = Yes"),
        "smoken":  ("Currently Smokes Cigarettes", "binary", "0 = No, 1 = Yes"),
        "drinkd":  ("Alcohol Drinking Days per Week", "score", "Days: 0 to 7 days a week"),
        "vigact":  ("Engages in Vigorous Exercise / Physical Activity", "binary", "0 = No, 1 = Yes"),
    },
    "Physical Independence & Daily Living": {
        "walkr":   ("Difficulty Walking Several Blocks", "binary", "0 = No difficulty, 1 = Has difficulty"),
        "dressa":  ("Difficulty Dressing Oneself (ADL)", "binary", "0 = No difficulty, 1 = Has difficulty"),
        "bathea":  ("Difficulty Taking a Bath or Shower (ADL)", "binary", "0 = No difficulty, 1 = Has difficulty"),
        "adl5a":   ("Count of Daily Living Difficulties (ADL Summary)", "score", "Count: 0 to 5 basic survival tasks impaired"),
        "iadl5a":  ("Count of Independent Living Difficulties (IADL Summary)", "score", "Count: 0 to 5 tasks impaired (handling money, meds, cooking)"),
        "bmi":     ("Body Mass Index (BMI)", "score", "Calculated weight / height squared (kg/m2)"),
    },
    "Social & Household Structure": {
        "mstat":   ("Marital Status Category", "scale", "1=Married, 2=Married (spouse away), 3=Partnered, 4=Separated, 5=Divorced, 7=Widowed, 8=Never married"),
        "child":   ("Total Number of Living Children", "score", "Number of children"),
        "hhres":   ("Total People Living in Household", "score", "Number of household residents"),
        "lbrf":    ("Labor Force Status", "scale", "1=Works full-time, 2=Works part-time, 4=Unemployed, 5=Partially retired, 6=Retired, 7=Disabled"),
        "itot":    ("Total Annual Household Income ($)", "score", "Dollar amount of all earnings, pensions, Social Security, and investments"),
    }
}

@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute("SET memory_limit = '3GB';")
    return con

con = get_con()

# Discover available wave parquet files
available_waves = sorted([
    os.path.basename(f).replace(".parquet", "")
    for f in glob.glob(f"{DATA_DIR}/r*.parquet")
    if not os.path.basename(f).startswith("s")
], key=lambda x: int(x.replace("r", "")))

st.sidebar.title("Study Controls")

# Step 1: Select Survey Wave
selected_wave = st.sidebar.selectbox(
    "1. Survey Year (Wave):",
    available_waves,
    index=1,
    format_func=lambda w: WAVE_INFO.get(w, (w, ""))[0]
)
wave_label, wave_year = WAVE_INFO.get(selected_wave, (selected_wave, 0))
wave_file = f"{DATA_DIR}/{selected_wave}.parquet"

# Inspect columns present in wave
wave_columns = set(con.execute(f"DESCRIBE SELECT * FROM '{wave_file}'").df()['column_name'].str.lower())

# Step 2: Select Research Topic
chosen_domain = st.sidebar.selectbox(
    "2. Health / Research Domain:",
    list(MEASURES_CATALOG.keys())
)

# Step 3: Select Specific Measure
domain_items = MEASURES_CATALOG[chosen_domain]
viable_measures = {}
for code, (label, mtype, guide) in domain_items.items():
    # Handle both r* (respondent) and h* (household) prefixes
    for prefix in [selected_wave, selected_wave.replace("r", "h")]:
        full_code = f"{prefix}{code}"
        if full_code in wave_columns:
            viable_measures[full_code] = (label, mtype, guide)

if not viable_measures:
    st.error(f"None of the measures in '{chosen_domain}' were administered in {wave_label}.")
    st.info("Remember: Cognitive batteries began systematically in 1996 (Wave 3). Choose another domain or wave.")
    st.stop()

selected_var = st.sidebar.selectbox(
    f"3. Select Measurement ({len(viable_measures)} available):",
    list(viable_measures.keys()),
    format_func=lambda v: f"{viable_measures[v][0]} ({v})"
)

clean_title, metric_type, meaning_guide = viable_measures[selected_var]

# Step 4: Survey Weights
wt_resp_col = f"{selected_wave}wtresp"
weight_options = {
    "Representative US Population Average (Recommended)": wt_resp_col if wt_resp_col in wave_columns else None,
    "Raw Unweighted Sample (Actual Survey Responses)": None
}
selected_weight_label = st.sidebar.selectbox("4. Population Weighting:", list(weight_options.keys()), index=0)
active_wt = weight_options[selected_weight_label]

# Resolve age variable
age_col = f"{selected_wave}agey_e" if f"{selected_wave}agey_e" in wave_columns else f"{selected_wave}age"

# Sidebar interpretation badge
st.sidebar.markdown("---")
st.sidebar.markdown(f"**How to Read This Metric:**\n\n*{meaning_guide}*")

# Query dataset
wt_select = f", w.{active_wt} AS survey_weight" if active_wt else ""
query = f"""
    SELECT 
        b.hhidpn,
        b.ragender,
        b.raeduc,
        w.{age_col} AS age,
        w.{selected_var} AS metric_val
        {wt_select}
    FROM '{DATA_DIR}/baseline_demographics.parquet' b
    JOIN '{wave_file}' w ON b.hhidpn = w.hhidpn
    WHERE w.{selected_var} IS NOT NULL 
      AND w.{age_col} IS NOT NULL
      AND b.ragender IS NOT NULL
"""

df = con.execute(query).df()

# Clean types
df['age'] = pd.to_numeric(df['age'], errors='coerce')
df['metric_val'] = pd.to_numeric(df['metric_val'], errors='coerce')
df['ragender'] = pd.to_numeric(df['ragender'], errors='coerce')
df['raeduc'] = pd.to_numeric(df['raeduc'], errors='coerce')

if active_wt:
    df['survey_weight'] = pd.to_numeric(df['survey_weight'], errors='coerce')
    df = df[df['survey_weight'] > 0]

df = df.dropna(subset=['age', 'metric_val', 'ragender'])

# Recode demographics to clear English
df["Gender"] = df["ragender"].map({1.0: "Male", 2.0: "Female"}).fillna("Unknown")
df["Education"] = df["raeduc"].map({
    1.0: "Less than High School",
    2.0: "GED",
    3.0: "High School Graduate",
    4.0: "Some College",
    5.0: "College Graduate & Above"
}).fillna("Unknown")

# Recode binary condition variables into human terms for plotting
if metric_type == "binary":
    df["Display Value"] = df["metric_val"].map({1.0: "Yes / Diagnosed", 0.0: "No / Unaffected"}).fillna("Other")
else:
    df["Display Value"] = df["metric_val"]

# Main Interface
st.title(f"{clean_title}")
st.caption(f"Survey Round: **{wave_label}** | Database Column: `{selected_var}` | Guide: *{meaning_guide}*")

# Top KPI metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Participants with Complete Answers", f"{len(df):,}")
c2.metric("Average Participant Age", f"{df['age'].mean():.1f} years")

if metric_type == "binary":
    if active_wt and 'survey_weight' in df.columns:
        pct = ((df['metric_val'] * df['survey_weight']).sum() / df['survey_weight'].sum()) * 100
        c3.metric("US Population Prevalence", f"{pct:.1f}%")
    else:
        pct = (df['metric_val'] == 1.0).mean() * 100
        c3.metric("Sample Prevalence", f"{pct:.1f}%")
else:
    if active_wt and 'survey_weight' in df.columns:
        w_avg = (df['metric_val'] * df['survey_weight']).sum() / df['survey_weight'].sum()
        c3.metric("US Population Average", f"{w_avg:.2f}")
    else:
        c3.metric("Sample Average", f"{df['metric_val'].mean():.2f}")

c4.metric("Women in Cohort", f"{(df['Gender'] == 'Female').mean() * 100:.1f}%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Distribution Breakdown", "📈 Trajectory Across Age & Education", "📋 Complete Participant Records"])

with tab1:
    st.subheader("How this metric is divided between Men and Women")
    if metric_type == "binary":
        fig_bar = px.histogram(
            df,
            x="Display Value",
            color="Gender",
            barmode="group",
            labels={"Display Value": "Diagnosis / Status", "count": "People"},
            title=f"Prevalence of {clean_title} by Gender"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        fig_hist = px.histogram(
            df,
            x="metric_val",
            color="Gender",
            barmode="overlay",
            marginal="box",
            labels={"metric_val": f"{clean_title} (Score)", "count": "People"},
            title=f"Distribution of {clean_title} by Gender"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    st.subheader("Age Trajectory by Education Level")
    sample_size = min(len(df), 3000)
    fig_scatter = px.scatter(
        df.sample(sample_size, random_state=42),
        x="age",
        y="metric_val",
        color="Education",
        trendline="ols",
        labels={"age": "Age in Years", "metric_val": clean_title},
        title=f"Age vs. {clean_title} Across Education Backgrounds"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab3:
    st.subheader("Complete Records Table")
    st.caption(f"Showing all **{len(df):,}** participants with validated answers:")

    export_df = df[["age", "Gender", "Education", "Display Value"]].copy()
    export_df.columns = ["Age (Years)", "Gender", "Education Background", f"{clean_title} ({selected_var})"]

    if active_wt and "survey_weight" in df.columns:
        export_df["US Population Weight"] = df["survey_weight"].round(1)

    st.dataframe(export_df, use_container_width=True, height=500)
