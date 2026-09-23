import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd
import glob
import json
import re
import os

st.set_page_config(layout="wide", page_title="RAND HRS Complete Research Workstation (1992–2022)")

DATA_DIR = "randhrs_parquet"

WAVE_INFO = {
    1: ("Wave 1 (1992)", 1992),
    2: ("Wave 2 (1994)", 1994),
    3: ("Wave 3 (1996)", 1996),
    4: ("Wave 4 (1998)", 1998),
    5: ("Wave 5 (2000)", 2000),
    6: ("Wave 6 (2002)", 2002),
    7: ("Wave 7 (2004)", 2004),
    8: ("Wave 8 (2006)", 2006),
    9: ("Wave 9 (2008)", 2008),
    10: ("Wave 10 (2010)", 2010),
    11: ("Wave 11 (2012)", 2012),
    12: ("Wave 12 (2014)", 2014),
    13: ("Wave 13 (2016)", 2016),
    14: ("Wave 14 (2018)", 2018),
    15: ("Wave 15 (2020)", 2020),
    16: ("Wave 16 (2022)", 2022)
}

SECTION_METADATA = {
    "Section A: Demographics, Identifiers & Weights": {
        "keywords": ["gender", "educ", "race", "hispan", "cohort", "wtresp", "wthh", "wtcrnh", "birth", "dead", "age", "mstat", "part"],
        "title": "Demographics, Survey Identifiers, Sampling & Weights",
        "description": "Baseline invariant demographics and time-varying survey weights. The study tracks individuals using household (HHID) and person (PN) identifiers combined into hhidpn. Sampling weights post-stratify the sample to match the U.S. Census Bureau/ACS population.",
        "key_vars": "hhidpn, ragender, raeduc, raracem, rahispan, r*wtresp."
    },
    "Section B: Physical Health & Medical Utilization": {
        "keywords": ["shlt", "hibp", "diab", "cancr", "lung", "heart", "strok", "arthr", "hosp", "nhm", "doc", "rx", "bmi", "smoke", "drink"],
        "title": "Chronic Physical Health & Health Care Utilization",
        "description": "Longitudinal doctor-diagnosed chronic disease indicators, general self-rated health, health behaviors, and healthcare service utilization (hospitalizations, nursing home stays, physician visits, prescription drugs).",
        "key_vars": "r*hibpe, r*diabe, r*cancre, r*stroke, r*hearte, r*shlt, r*bmi."
    },
    "Section C: Functional Limitations & Helpers": {
        "keywords": ["walk", "dress", "bath", "eat", "bed", "adl", "iadl", "chair", "climb", "stoop", "lift", "dime", "phone", "money", "meds", "help"],
        "title": "Functional Limitations, ADLs, IADLs & Caregiving Helpers",
        "description": "Physical mobility, large muscle endurance, fine motor skills, Activities of Daily Living (ADLs: dressing, bathing, eating, walking across a room, getting into/out of bed), and Instrumental Activities of Daily Living (IADLs).",
        "key_vars": "r*adl5a, r*iadl5a, r*walkr, r*dressa."
    },
    "Section D: Financial & Housing Wealth": {
        "keywords": ["atot", "aoth", "ahous", "amort", "astck", "abond", "achck", "acd", "aira", "absns", "aveh", "adebt", "netw"],
        "title": "Financial, Housing & Net Wealth Imputations",
        "description": "Comprehensive asset and debt accounting at the household level. Imputed using unfolding brackets and cross-wave asset reconciliations.",
        "key_vars": "h*atotb (Total Net Wealth), h*ahous (Primary residence), h*amort (Mortgages), h*astck (Stocks), h*aira (IRAs)."
    },
    "Section E: Income & Transfers": {
        "keywords": ["itot", "iearn", "isoc", "issi", "ipen", "icap", "iunemp", "igov", "irat", "pov"],
        "title": "Income, Social Transfers & Poverty Metrics",
        "description": "Calendar-year household and individual income streams, including earnings, pensions, annuities, Social Security retirement benefits, SSI, and government transfers.",
        "key_vars": "h*itot, r*iearn, r*isoc, h*inpov."
    },
    "Section F: Social Security & Disability Episodes": {
        "keywords": ["di", "ssdi", "ssi", "appe", "reap", "disab", "socsec", "rad"],
        "title": "Social Security Disability (SSDI) & SSI History",
        "description": "Reconstructed historical records of SSDI and SSI disability claims, application outcomes, appeals, benefit receipt, and terminations across up to 11 longitudinal episodes.",
        "key_vars": "radnepi, r*di, radappm*, radappy*."
    },
    "Section G: Pensions & Retirement Plans": {
        "keywords": ["pen", "dcbal", "contrib", "curjob", "db", "dc"],
        "title": "Employer Pension Plans & Account Balances",
        "description": "Classifications of employer-provided retirement accounts from current and past jobs, differentiating between Defined Benefit (DB) and Defined Contribution (DC 401k/403b).",
        "key_vars": "r*dcbal1, r*curjob, r*typf1."
    },
    "Section H: Health Insurance & Coverage": {
        "keywords": ["gov", "mcaid", "mcare", "priv", "phi", "hmo", "ins", "partd", "ltc"],
        "title": "Health Insurance, Medicare & Long-Term Care",
        "description": "Coverage across Medicare Parts A, B, and D, Medicaid, employer-provided retiree health insurance, HMO enrollments, and private Long-Term Care policies.",
        "key_vars": "r*higov, r*covrt, r*ltc."
    },
    "Section I: Family Structure & Living Arrangements": {
        "keywords": ["child", "hhres", "livsib", "livpar", "fam"],
        "title": "Family Structure, Kinship Networks & Living Arrangements",
        "description": "Household rosters, counts of resident and non-resident family members, living children, surviving parents, and living siblings.",
        "key_vars": "h*child, h*hhres, r*livsib, momliv, dadliv."
    },
    "Section J: Retirement Expectations & Subjective Probabilities": {
        "keywords": ["ret", "retw", "prob", "p75", "p85", "work62", "work65", "bequest", "inher"],
        "title": "Retirement Expectations & Subjective Probabilities",
        "description": "Subjective probabilistic expectations on 0–100 scales: probability of living to age 75 or 85, working full-time past age 62/65, leaving an inheritance, and risk aversion.",
        "key_vars": "r*liv75, r*liv85, r*work62."
    },
    "Section K: Employment History & Job Demands": {
        "keywords": ["work", "lbrf", "wage", "wgi", "hour", "tenur", "ind", "occ", "effort", "stress"],
        "title": "Labor Force Participation, Wages & Physical Job Demands",
        "description": "Employment trajectories, weekly hours, annual weeks worked, hourly wage rates, job tenure, occupation/industry codes, and physical job demands.",
        "key_vars": "r*lbrf, r*wgihr, r*jlen, r*effort."
    },
    "Section L: Psychosocial & Lifestyle Measures": {
        "keywords": ["lonely", "stress", "purp", "optim", "pessim", "social", "percep"],
        "title": "Psychosocial Scales, Life Satisfaction & Well-Being",
        "description": "Administered via rotating 'Leave-Behind' questionnaires, evaluating Big Five personality traits, UCLA Loneliness Scale, perceived chronic stress, and purpose in life.",
        "key_vars": "r*lonely, r*stress, r*purp."
    }
}

@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute("SET memory_limit = '3GB';")
    return con

con = get_con()

@st.cache_data
def load_catalog():
    if os.path.exists("variable_catalog.json"):
        with open("variable_catalog.json", "r") as f:
            raw = json.load(f)
            norm = {}
            for k, v in raw.items():
                norm[k] = v
                norm[k.lower()] = v
                norm[k.upper()] = v
            return norm
    return {}

catalog = load_catalog()

def get_clean_label(col_name):
    col_str = str(col_name).strip()
    if col_str in catalog:
        return catalog[col_str]
    if col_str.lower() in catalog:
        return catalog[col_str.lower()]
    match = re.search(r'^[rsh]\d+(.+)$', col_str.lower())
    if match:
        root = match.group(1)
        for cand in [root, f"r{root}", f"h{root}", f"s{root}"]:
            if cand in catalog:
                return catalog[cand]
    return f"{col_str}"

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.title("Study Controls")

target_mode = st.sidebar.radio(
    "1. Analytical Domain / Target:",
    [
        "Living Waves: Respondent (r)",
        "Living Waves: Spouse (s)",
        "Lifetime / Invariant Baseline Data (Demographics & Spells)",
        "Exit & End-of-Life Data (re/rad)"
    ],
    index=0
)

# ----------------- ROUTING LOGIC -----------------
is_exit = target_mode.startswith("Exit")
is_baseline = "Baseline" in target_mode

if is_baseline:
    wave_label, wave_year = "Baseline Demographics & Spells", 0
    wave_file = f"{DATA_DIR}/baseline_demographics.parquet"
    role_prefix = "ra"
elif is_exit:
    wave_label, wave_year = "Exit & End-of-Life", 0
    wave_file = f"{DATA_DIR}/baseline_demographics.parquet"
    role_prefix = "re"
else:
    role_prefix = "r" if "Respondent" in target_mode else "s"
    selected_wave = st.sidebar.selectbox(
        "2. Survey Wave (Year):",
        options=list(WAVE_INFO.keys()),
        index=13,
        format_func=lambda w: WAVE_INFO[w][0]
    )
    wave_label, wave_year = WAVE_INFO[selected_wave]
    wave_file = f"{DATA_DIR}/{role_prefix}{selected_wave}.parquet"

if not os.path.exists(wave_file):
    st.error(f"Partition file `{wave_file}` was not found.")
    st.stop()

# Retrieve column names
desc_df = con.execute(f"DESCRIBE SELECT * FROM '{wave_file}'").df()
wave_columns = {col.lower(): col for col in desc_df['column_name']}

CORE_IGNORED = {"hhidpn", "hhid", "pn"}
if is_exit:
    measure_columns = [col for col in wave_columns.keys() if (col.startswith("re") or col.startswith("rad")) and col not in CORE_IGNORED]
elif is_baseline:
    measure_columns = [col for col in wave_columns.keys() if not (col.startswith("re") or col.startswith("rad")) and col not in CORE_IGNORED]
else:
    measure_columns = [col for col in wave_columns.keys() if col not in CORE_IGNORED]

# Categorize into 12 sections
categorized_vars = {sec: [] for sec in SECTION_METADATA.keys()}
categorized_vars["Section Other: Additional Harmonized Variables"] = []

for c in sorted(measure_columns):
    assigned = False
    for sec, meta in SECTION_METADATA.items():
        if any(kw in c for kw in meta["keywords"]):
            categorized_vars[sec].append(c)
            assigned = True
            break
    if not assigned:
        categorized_vars["Section Other: Additional Harmonized Variables"].append(c)

chosen_section = st.sidebar.selectbox(
    "3. Codebook Section:",
    options=[sec for sec in categorized_vars.keys() if len(categorized_vars[sec]) > 0]
)

viable_vars = categorized_vars[chosen_section]

def format_var_option(v):
    original_col = wave_columns.get(v, v)
    desc = get_clean_label(original_col)
    if len(desc) > 60:
        return f"{desc[:60]}... [{original_col}]"
    return f"{desc} [{original_col}]"

selected_col_lower = st.sidebar.selectbox(
    f"4. Variable ({len(viable_vars):,} in this section):",
    viable_vars,
    format_func=format_var_option
)
actual_col_name = wave_columns[selected_col_lower]
clean_description = get_clean_label(actual_col_name)

# Weight handling
if not (is_baseline or is_exit):
    wt_candidate = f"r{selected_wave}wtresp".lower()
    has_weights = (role_prefix == 'r' and wt_candidate in wave_columns)
    actual_wt_col = wave_columns.get(wt_candidate) if has_weights else None
else:
    actual_wt_col = None

weight_options = {
    "Representative US Population Average (wtresp)": actual_wt_col if actual_wt_col else None,
    "Raw Unweighted Sample": None
}
selected_weight_label = st.sidebar.selectbox("5. Population Weighting:", list(weight_options.keys()), index=0)
active_wt = weight_options[selected_weight_label]

# Age resolution
if not (is_baseline or is_exit):
    candidate_ages = [
        f"{role_prefix}{selected_wave}agey_e".lower(),
        f"{role_prefix}{selected_wave}age".lower(),
        f"r{selected_wave}agey_e".lower(),
        f"r{selected_wave}age".lower()
    ]
    found_age_col = next((wave_columns[ca] for ca in candidate_ages if ca in wave_columns), None)
    if found_age_col:
        age_expression = f"TRY_CAST(w.{found_age_col} AS DOUBLE)"
    else:
        age_expression = f"({wave_year} - TRY_CAST(b.rabyear AS DOUBLE))"
else:
    age_expression = "TRY_CAST(b.radage_y AS DOUBLE)"

# ----------------- DATA QUERY & PROCESSING -----------------
wt_select = f", TRY_CAST(w.{active_wt} AS DOUBLE) AS survey_weight" if active_wt else ""
if is_baseline or is_exit:
    query = f"""
        SELECT 
            b.hhidpn,
            TRY_CAST(b.ragender AS DOUBLE) AS ragender,
            TRY_CAST(b.raeduc AS DOUBLE) AS raeduc,
            {age_expression} AS age,
            TRY_CAST(b.{actual_col_name} AS DOUBLE) AS metric_val
        FROM '{DATA_DIR}/baseline_demographics.parquet' b
        WHERE TRY_CAST(b.{actual_col_name} AS DOUBLE) IS NOT NULL 
          AND TRY_CAST(b.{actual_col_name} AS DOUBLE) >= 0
          AND TRY_CAST(b.ragender AS DOUBLE) IS NOT NULL
    """
else:
    query = f"""
        SELECT 
            b.hhidpn,
            TRY_CAST(b.ragender AS DOUBLE) AS ragender,
            TRY_CAST(b.raeduc AS DOUBLE) AS raeduc,
            {age_expression} AS age,
            TRY_CAST(w.{actual_col_name} AS DOUBLE) AS metric_val
            {wt_select}
        FROM '{DATA_DIR}/baseline_demographics.parquet' b
        JOIN '{wave_file}' w ON b.hhidpn = w.hhidpn
        WHERE TRY_CAST(w.{actual_col_name} AS DOUBLE) IS NOT NULL 
          AND TRY_CAST(w.{actual_col_name} AS DOUBLE) >= 0
          AND {age_expression} IS NOT NULL
          AND {age_expression} > 0
          AND TRY_CAST(b.ragender AS DOUBLE) IS NOT NULL
    """

df = con.execute(query).df()

if df.empty or 'metric_val' not in df.columns:
    st.error(f"No valid numeric data found for `{actual_col_name}` ({clean_description}) in this section.")
    st.stop()

if active_wt and 'survey_weight' in df.columns:
    df = df[df['survey_weight'] > 0]

df = df.dropna(subset=['metric_val', 'ragender'])

df["Gender"] = df["ragender"].map({1.0: "Male", 2.0: "Female"}).fillna("Unknown")
df["Education"] = df["raeduc"].map({
    1.0: "Less than High School",
    2.0: "GED",
    3.0: "High School Graduate",
    4.0: "Some College",
    5.0: "College Graduate & Above"
}).fillna("Unknown")

unique_vals = set(df['metric_val'].unique())
is_binary = unique_vals.issubset({0.0, 1.0})
is_discrete = len(unique_vals) <= 10 and not is_binary

# ----------------- MAIN UI HEADER -----------------
st.title(f"{clean_description}")

current_meta = SECTION_METADATA.get(chosen_section, {
    "title": "Harmonized Survey Measures",
    "description": "Additional longitudinal indices created by the RAND Center for the Study of Aging.",
    "key_vars": "Varies by selected module."
})

st.markdown(f"""
> ### 📘 {current_meta['title']}
> **Domain Overview:** {current_meta['description']}
> 
> * **Core Measures in this Domain:** {current_meta['key_vars']}
""")

with st.expander("🔍 Click to view Deep-Dive Details for this Specific Variable", expanded=True):
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown(f"**Plain English Description:** {clean_description}")
        st.markdown(f"**Stata Column Code:** `{actual_col_name}`")
        st.markdown(f"**Survey Interview Round:** {wave_label}")
    with col_v2:
        st.markdown(f"**Target Person / Domain:** {target_mode}")
        st.markdown(f"**Data Type / Scale:** {'Binary (0 = No/Absent, 1 = Yes/Present)' if is_binary else ('Discrete Rating / Score' if is_discrete else 'Continuous Numerical Value')}")
        st.markdown(f"**Weighting State:** {'US Population Representative (wtresp)' if active_wt else 'Raw Unweighted Sample Responses'}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Participants in Selection", f"{len(df):,}")
if 'age' in df.columns and df['age'].notnull().any():
    c2.metric("Average Participant Age", f"{df['age'].dropna().mean():.1f} yrs")
else:
    c2.metric("Average Participant Age", "N/A")

if is_binary:
    if active_wt and 'survey_weight' in df.columns:
        pct = ((df['metric_val'] * df['survey_weight']).sum() / df['survey_weight'].sum()) * 100
        c3.metric("US Population Prev.", f"{pct:.1f}%")
    else:
        c3.metric("Sample Prev.", f"{(df['metric_val'] == 1.0).mean() * 100:.1f}%")
else:
    if active_wt and 'survey_weight' in df.columns:
        w_avg = (df['metric_val'] * df['survey_weight']).sum() / df['survey_weight'].sum()
        c3.metric("Weighted Average", f"{w_avg:,.2f}")
    else:
        c3.metric("Sample Average", f"{df['metric_val'].mean():,.2f}")

c4.metric("Women in Cohort", f"{(df['Gender'] == 'Female').mean() * 100:.1f}%")

st.markdown("---")

# ----------------- TABS -----------------
tab_overview, tab_heatmap, tab_traj, tab_dist, tab_scatter, tab_table, tab_multi, tab_search = st.tabs([
    "📖 Study & Architecture Overview",
    "🔥 Disease Trajectory Heatmap",
    "📈 30-Year Trajectory (1992–2022)",
    "📊 Wave Distribution",
    "🎯 Age Gradient (Cross-Section)",
    "📋 Single-Variable Records",
    "📑 Multi-Column Dataset Explorer",
    "🔍 Global Search & Catalog Lookup"
])

# ---------------- TAB 0: SYSTEM OVERVIEW & TUTORIAL ----------------
with tab_overview:
    st.subheader("How the RAND Health and Retirement Study (HRS) is Structured")
    st.markdown("""
    The **Health and Retirement Study (HRS)** is a longitudinal survey of 45,234 Americans aged 50 and older[cite: 1].
    Every two years (a **Wave**), the survey conducts core interviews with respondents and their spouses[cite: 1].
    
    ---
    ### 1. The Variable Naming Convention
    * **First Character:** `r` (Respondent), `s` (Spouse), `h` (Household), `re` (Exit post-mortem), `rad` (Reconstructed disability episodes)[cite: 1].
    * **Second Part:** Survey wave number (`1` = 1992, `2` = 1994 ... `16` = 2022)[cite: 1].
    * **Remaining Part:** The conceptual variable root (e.g. `hibpe` = Hypertension, `diabe` = Diabetes, `cogtot` = Memory score)[cite: 1].
    
    ---
    ### 2. The 4 Analytical Domains
    1. **Living Waves (Respondent):** Primary interviews covering health, memory, finances, and employment across all 16 survey waves (`r1` to `r16`)[cite: 1].
    2. **Living Waves (Spouse):** Matched spousal files (`s1` to `s16`) allowing spousal pairs and caregiving dyads to be inspected[cite: 1].
    3. **Lifetime / Invariant Baseline Data:** Invariant demographics (birth dates, education, veteran status, entry cohorts, and all 11 SSDI episodes)[cite: 1].
    4. **Exit & End-of-Life Data (`re`):** Post-mortem proxy interviews covering circumstances of death, hospice care, and terminal medical costs[cite: 1].
    """)

# ---------------- TAB 1: DISEASE TRANSITION HEATMAP ----------------
@st.cache_data
def compute_disease_transition_matrix():
    diseases = {
        "hibpe": "Hypertension",
        "diabe": "Diabetes",
        "cancre": "Cancer",
        "lunge": "Lung Disease",
        "hearte": "Heart Disease",
        "stroke": "Stroke",
        "arthre": "Arthritis"
    }
    keys = list(diseases.keys())
    transitions = {a: {b: 0 for b in keys if b != a} for a in keys}
    eligible = {a: {b: 0 for b in keys if b != a} for a in keys}
    
    con_hm = duckdb.connect()
    con_hm.execute("SET memory_limit = '3GB';")
    
    for w in range(1, 16):
        w_curr = f"{DATA_DIR}/r{w}.parquet"
        w_next = f"{DATA_DIR}/r{w+1}.parquet"
        if not (os.path.exists(w_curr) and os.path.exists(w_next)):
            continue
            
        curr_cols = set(con_hm.execute(f"DESCRIBE SELECT * FROM '{w_curr}'").df()['column_name'].str.lower())
        next_cols = set(con_hm.execute(f"DESCRIBE SELECT * FROM '{w_next}'").df()['column_name'].str.lower())
        
        select_parts = ["c.hhidpn"]
        for k in keys:
            c_col = f"r{w}{k}"
            n_col = f"r{w+1}{k}"
            if c_col in curr_cols and n_col in next_cols:
                select_parts.append(f"TRY_CAST(c.{c_col} AS INT) AS c_{k}")
                select_parts.append(f"TRY_CAST(n.{n_col} AS INT) AS n_{k}")
            else:
                select_parts.append(f"NULL AS c_{k}")
                select_parts.append(f"NULL AS n_{k}")
                
        sql = f"""
            SELECT {', '.join(select_parts)}
            FROM '{w_curr}' c
            JOIN '{w_next}' n ON c.hhidpn = n.hhidpn
        """
        pair_df = con_hm.execute(sql).df()
        
        for a in keys:
            for b in keys:
                if a == b:
                    continue
                subset = pair_df[(pair_df[f"c_{a}"] == 1) & (pair_df[f"c_{b}"] == 0)]
                n_eligible = len(subset)
                if n_eligible > 0:
                    n_transitioned = len(subset[subset[f"n_{b}"] == 1])
                    eligible[a][b] += n_eligible
                    transitions[a][b] += n_transitioned

    matrix = []
    for a in keys:
        row = []
        for b in keys:
            if a == b:
                row.append(0.0)
            else:
                denom = eligible[a][b]
                num = transitions[a][b]
                rate = (num / denom * 100) if denom > 0 else 0.0
                row.append(round(rate, 2))
        matrix.append(row)
        
    labels = [diseases[k] for k in keys]
    return pd.DataFrame(matrix, index=labels, columns=labels)

with tab_heatmap:
    st.subheader("🔥 Longitudinal Disease Precedence & Transition Matrix")
    st.caption("Tracks how one chronic diagnosis acts as a gateway to subsequent chronic conditions across consecutive waves.")
    
    with st.spinner("Calculating disease transitions across 30 years of interviews..."):
        matrix_df = compute_disease_transition_matrix()
        
    fig_heat = px.imshow(
        matrix_df,
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="Subsequent Condition Developed (Wave t+1)", 
                    y="Initial Condition (Wave t)", 
                    color="2-Yr Incident Risk (%)"),
        title="Probabilistic Disease Transition Matrix (1992–2022)"
    )
    fig_heat.update_layout(height=550)
    st.plotly_chart(fig_heat, use_container_width=True)
    
    with st.expander("View Numerical Percentage Matrix"):
        st.dataframe(matrix_df.style.format("{:.2f}%"))

# ---------------- TAB 2: 30-YEAR TRAJECTORY ----------------
match = re.search(r'^[rsh]\d+(.+)$', selected_col_lower)
root_code = match.group(1) if match else selected_col_lower

with tab_traj:
    st.subheader(f"Longitudinal Trajectory: {clean_description}")
    st.caption(f"Tracing `{actual_col_name}` across all 16 survey rounds (1992 to 2022).")
    
    if is_baseline or is_exit:
        st.info("The selected analytical domain contains baseline or exit data. To view 30-year trajectories across all 16 waves, choose 'Living Waves: Respondent' or 'Living Waves: Spouse' in the sidebar.")
    else:
        trajectory_rows = []
        for w_num, (w_name, w_yr) in WAVE_INFO.items():
            w_path = f"{DATA_DIR}/{role_prefix}{w_num}.parquet"
            if not os.path.exists(w_path):
                continue
                
            w_cols_desc = con.execute(f"DESCRIBE SELECT * FROM '{w_path}'").df()
            w_col_map = {col.lower(): col for col in w_cols_desc['column_name']}
            
            target_cand = f"{role_prefix}{w_num}{root_code}".lower()
            if target_cand not in w_col_map:
                continue
            actual_target_col = w_col_map[target_cand]
            
            wt_c_cand = f"r{w_num}wtresp".lower()
            if role_prefix == 'r' and wt_c_cand in w_col_map:
                actual_wt = w_col_map[wt_c_cand]
                wt_sub = f", TRY_CAST(w.{actual_wt} AS DOUBLE) AS w_wt"
            else:
                wt_sub = ", 1.0 AS w_wt"
            
            traj_sql = f"""
                SELECT 
                    {w_yr} AS year,
                    '{w_name}' AS wave_name,
                    TRY_CAST(w.{actual_target_col} AS DOUBLE) AS val,
                    TRY_CAST(b.ragender AS DOUBLE) AS ragender
                    {wt_sub}
                FROM '{w_path}' w
                JOIN '{DATA_DIR}/baseline_demographics.parquet' b ON w.hhidpn = b.hhidpn
                WHERE TRY_CAST(w.{actual_target_col} AS DOUBLE) IS NOT NULL 
                  AND TRY_CAST(w.{actual_target_col} AS DOUBLE) >= 0
                  AND TRY_CAST(b.ragender AS DOUBLE) IN (1, 2)
            """
            temp_df = con.execute(traj_sql).df()
            if not temp_df.empty and 'ragender' in temp_df.columns:
                temp_df['Gender'] = temp_df['ragender'].map({1.0: "Male", 2.0: "Female"})
                temp_df['w_wt'] = pd.to_numeric(temp_df['w_wt'], errors='coerce').fillna(1.0)
                
                for gender in ["Male", "Female"]:
                    sub = temp_df[temp_df['Gender'] == gender]
                    if len(sub) > 0 and sub['w_wt'].sum() > 0:
                        if is_binary:
                            val_out = ((sub['val'] == 1.0) * sub['w_wt']).sum() / sub['w_wt'].sum() * 100
                        else:
                            val_out = (sub['val'] * sub['w_wt']).sum() / sub['w_wt'].sum()
                        trajectory_rows.append({
                            "Year": w_yr,
                            "Wave": w_name,
                            "Gender": gender,
                            "Rate": val_out
                        })

        if trajectory_rows:
            traj_df = pd.DataFrame(trajectory_rows)
            y_label = "Prevalence (%)" if is_binary else f"Average {clean_description}"
            fig_trend = px.line(
                traj_df, x="Year", y="Rate", color="Gender", markers=True,
                title=f"Longitudinal Trajectory: {clean_description} by Gender",
                labels={"Rate": y_label}
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Continuous cross-wave data is not available for this metric.")

# ---------------- TAB 3: DISTRIBUTION ----------------
with tab_dist:
    st.subheader(f"Breakdown in {wave_label}")
    if is_binary:
        df["Display"] = df["metric_val"].map({1.0: "Yes / Affirmed", 0.0: "No / Negative"}).fillna("Other")
        fig_bar = px.histogram(df, x="Display", color="Gender", barmode="group", labels={"Display": clean_description}, title=f"Prevalence in {wave_label}")
        st.plotly_chart(fig_bar, use_container_width=True)
    elif is_discrete:
        fig_bar = px.histogram(df, x="metric_val", color="Gender", barmode="group", labels={"metric_val": clean_description}, title=f"Score / Category Breakdown in {wave_label}")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        fig_hist = px.histogram(df, x="metric_val", color="Gender", barmode="overlay", marginal="box", labels={"metric_val": clean_description}, title=f"Continuous Distribution in {wave_label}")
        st.plotly_chart(fig_hist, use_container_width=True)

# ---------------- TAB 4: CROSS-SECTION ----------------
with tab_scatter:
    st.subheader(f"Age Gradient in {wave_label}")
    if 'age' in df.columns and df['age'].notnull().any():
        sample_size = min(len(df), 3000)
        fig_scatter = px.scatter(
            df.sample(sample_size, random_state=42), x="age", y="metric_val", color="Education",
            trendline="ols", labels={"age": "Age (Years)", "metric_val": clean_description},
            title=f"Age vs. {clean_description} Across Education Tiers ({wave_label})"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Age variable is not available for this demographic selection.")

# ---------------- TAB 5: SINGLE VARIABLE RECORDS ----------------
with tab_table:
    st.subheader(f"Underlying Records: {clean_description}")
    
    view_df = pd.DataFrame()
    view_df["Participant ID (hhidpn)"] = df["hhidpn"]
    if 'age' in df.columns:
        view_df["Age"] = df["age"].round(1)
    view_df["Gender"] = df["Gender"]
    view_df["Education"] = df["Education"]
    
    if is_binary:
        view_df[f"{clean_description} (Raw)"] = df["metric_val"].astype(int)
        view_df["Status"] = df["metric_val"].map({1: "Yes", 0: "No"}).fillna("Other")
    else:
        view_df[f"{clean_description} ({actual_col_name})"] = df["metric_val"]
        
    if active_wt and "survey_weight" in df.columns:
        view_df["Population Weight"] = df["survey_weight"].round(2)
        
    col_a, col_b = st.columns(2)
    col_a.metric("Rows Displayed", f"{len(view_df):,}")
    
    csv_data = view_df.to_csv(index=False).encode('utf-8')
    col_b.download_button(
        label="📥 Download Table as CSV",
        data=csv_data,
        file_name=f"randhrs_{actual_col_name}.csv",
        mime="text/csv",
    )
    st.dataframe(view_df, use_container_width=True, height=500)

# ---------------- TAB 6: MULTI-COLUMN DATASET EXPLORER ----------------
with tab_multi:
    st.subheader(f"Multi-Column Dataset Explorer ({wave_label})")
    st.caption("Inspect and read any arbitrary slice of raw columns side-by-side.")
    
    all_available_cols = sorted(list(wave_columns.values()))
    default_picks = [actual_col_name] if actual_col_name in all_available_cols else []
    
    multi_selected = st.multiselect(
        "Choose columns to display together:",
        all_available_cols,
        default=default_picks,
        format_func=lambda x: f"{x} — {get_clean_label(x)[:50]}"
    )
    
    if multi_selected:
        col_list_str = ", ".join([f"w.{col}" for col in multi_selected])
        if is_baseline or is_exit:
            multi_sql = f"""
                SELECT 
                    w.hhidpn,
                    TRY_CAST(w.ragender AS DOUBLE) as ragender,
                    {col_list_str}
                FROM '{DATA_DIR}/baseline_demographics.parquet' w
                LIMIT 5000
            """
        else:
            multi_sql = f"""
                SELECT 
                    b.hhidpn,
                    TRY_CAST(b.ragender AS DOUBLE) as ragender,
                    {col_list_str}
                FROM '{DATA_DIR}/baseline_demographics.parquet' b
                JOIN '{wave_file}' w ON b.hhidpn = w.hhidpn
                LIMIT 5000
            """
        mdf = con.execute(multi_sql).df()
        mdf["Gender"] = mdf["ragender"].map({1.0: "Male", 2.0: "Female"}).fillna("Unknown")
        mdf = mdf.drop(columns=["ragender"])
        
        st.write(f"Displaying first **{len(mdf):,}** rows:")
        st.dataframe(mdf, use_container_width=True, height=500)
        
        mcsv = mdf.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Multi-Column Slice as CSV",
            data=mcsv,
            file_name="randhrs_multicolumn_slice.csv",
            mime="text/csv"
        )
    else:
        st.info("Select one or more variables from the dropdown above to display the table.")

# ---------------- TAB 7: GLOBAL CATALOG SEARCH ----------------
with tab_search:
    st.subheader("Global Variable Search (All 19,000+ Variables)")
    st.caption("Search across the entire official RAND dictionary.")
    
    search_term = st.text_input("Type any keyword (e.g., 'alzheimer', 'insulin', 'pension', 'mortgage'):", "insulin")
    
    if search_term and catalog:
        matches = [
            {"Column": k, "Description": v}
            for k, v in catalog.items()
            if (search_term.lower() in v.lower() or search_term.lower() in k.lower()) and not k.isupper()
        ][:100]
        
        if matches:
            st.write(f"Found **{len(matches)}** matching variables:")
            st.dataframe(pd.DataFrame(matches), use_container_width=True)
        else:
            st.warning("No variables matched that keyword.")
