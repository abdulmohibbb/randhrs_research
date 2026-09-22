import duckdb
import pandas as pd
import os

DATA_DIR = "randhrs_parquet"
con = duckdb.connect()
con.execute("SET memory_limit = '3GB';")

# All 16 waves
waves = [f"r{i}" for i in range(1, 17)]

# Full dictionary of measurements across the 5 domains
master_catalog = [
    # Baseline Totals
    ("Total Pool", "Total People Interviewed", "hhidpn", "hhidpn"),
    
    # Domain 1: Chronic Health Conditions
    ("Chronic Health Conditions", "High Blood Pressure (Doctor Diagnosed)", "r*hibpe", "hibpe"),
    ("Chronic Health Conditions", "High Blood Pressure (Diagnosed or Meds)", "r*hibpe2", "hibpe2"),
    ("Chronic Health Conditions", "Diabetes (Doctor Diagnosed)", "r*diabe", "diabe"),
    ("Chronic Health Conditions", "Diabetes (Diagnosed or Insulin/Pills)", "r*diabe2", "diabe2"),
    ("Chronic Health Conditions", "Heart Disease or Heart Attack", "r*hearte", "hearte"),
    ("Chronic Health Conditions", "Stroke (Doctor Diagnosed)", "r*stroke", "stroke"),
    ("Chronic Health Conditions", "Cancer (Any type except skin)", "r*cancre", "cancre"),
    ("Chronic Health Conditions", "Chronic Lung Disease (COPD/Asthma)", "r*lunge", "lunge"),
    ("Chronic Health Conditions", "Arthritis or Rheumatism", "r*arthre", "arthre"),
    ("Chronic Health Conditions", "Chronic Conditions Count (0-8)", "r*conde", "conde"),
    ("Chronic Health Conditions", "Self-Reported Health (1=Exc, 5=Poor)", "r*shlt", "shlt"),
    
    # Domain 2: Memory & Cognitive Function
    ("Memory & Cognition", "Immediate Word Recall (0-10)", "r*imtot", "imtot"),
    ("Memory & Cognition", "Delayed Word Recall (0-10)", "r*dltot", "dltot"),
    ("Memory & Cognition", "Serial 7s Subtraction (0-5)", "r*ser7", "ser7"),
    ("Memory & Cognition", "Backwards Count 20 (0/1)", "r*bwc20", "bwc20"),
    ("Memory & Cognition", "Composite Cognitive Score (0-35)", "r*cogtot", "cogtot"),
    ("Memory & Cognition", "27-Point Cognitive Battery (0-27)", "r*cogtot27", "cogtot27"),
    
    # Domain 3: Mental Health & Behaviors
    ("Mental Health & Behaviors", "CES-D Depression Score (0-8)", "r*cesd", "cesd"),
    ("Mental Health & Behaviors", "Ever Smoked Cigarettes", "r*smokev", "smokev"),
    ("Mental Health & Behaviors", "Currently Smokes Cigarettes", "r*smoken", "smoken"),
    ("Mental Health & Behaviors", "Alcohol Drinking Days/Week", "r*drinkd", "drinkd"),
    ("Mental Health & Behaviors", "Vigorous Physical Activity", "r*vigact", "vigact"),
    
    # Domain 4: Daily Living & Independence (ADLs/IADLs)
    ("Daily Living & Independence", "Difficulty Walking Several Blocks", "r*walkr", "walkr"),
    ("Daily Living & Independence", "Difficulty Dressing Self (ADL)", "r*dressa", "dressa"),
    ("Daily Living & Independence", "Difficulty Bathing Self (ADL)", "r*bathea", "bathea"),
    ("Daily Living & Independence", "Difficulty Eating (ADL)", "r*eata", "eata"),
    ("Daily Living & Independence", "Difficulty Getting Out of Bed (ADL)", "r*beda", "beda"),
    ("Daily Living & Independence", "Impaired ADL Count (0-5)", "r*adl5a", "adl5a"),
    ("Daily Living & Independence", "Impaired IADL Count (0-5)", "r*iadl5a", "iadl5a"),
    ("Daily Living & Independence", "Body Mass Index (BMI)", "r*bmi", "bmi"),
    
    # Domain 5: Socioeconomics & Family
    ("Socioeconomics & Family", "Marital Status", "r*mstat", "mstat"),
    ("Socioeconomics & Family", "Number of Living Children", "h*child", "child"),
    ("Socioeconomics & Family", "Household Resident Count", "h*hhres", "hhres"),
    ("Socioeconomics & Family", "Labor Force Status", "r*lbrf", "lbrf"),
    ("Socioeconomics & Family", "Total Household Annual Income ($)", "h*itot", "itot"),
    ("Socioeconomics & Family", "Total Household Net Wealth ($)", "h*atotb", "atotb"),
    
    # Weights
    ("Population Weights", "Respondent Sampling Weight", "r*wtresp", "wtresp"),
    ("Population Weights", "Combined Nursing Home Weight", "r*wtcrnh", "wtcrnh"),
    ("Population Weights", "Household Analysis Weight", "h*weight", "weight")
]

rows = []
print("Auditing all 16 waves across all domains and measurements...")

for domain, plain_name, code_pattern, raw_suffix in master_catalog:
    row_data = {
        "Research Domain": domain,
        "Measurement (Plain English)": plain_name,
        "Variable Pattern": code_pattern
    }
    
    for w in waves:
        wave_file = f"{DATA_DIR}/{w}.parquet"
        if not os.path.exists(wave_file):
            row_data[w.upper()] = "File Missing"
            continue
            
        columns = set(con.execute(f"DESCRIBE SELECT * FROM '{wave_file}'").df()['column_name'].str.lower())
        
        # Test prefixes: r* or h*
        target_col = None
        if raw_suffix == "hhidpn":
            target_col = "hhidpn"
        elif f"{w}{raw_suffix}" in columns:
            target_col = f"{w}{raw_suffix}"
        elif f"{w.replace('r', 'h')}{raw_suffix}" in columns:
            target_col = f"{w.replace('r', 'h')}{raw_suffix}"
            
        if target_col and target_col in columns:
            # Query exact non-null count
            count_query = f"SELECT COUNT({target_col}) FROM '{wave_file}' WHERE {target_col} IS NOT NULL"
            val_count = con.execute(count_query).fetchone()[0]
            row_data[w.upper()] = f"{val_count:,}"
        else:
            row_data[w.upper()] = "-"
            
    rows.append(row_data)

df_roadmap = pd.DataFrame(rows)

# Save to CSV for Excel
output_csv = "randhrs_complete_roadmap_all_waves.csv"
df_roadmap.to_csv(output_csv, index=False)

print(f"\n Master roadmap created successfully: '{output_csv}'")
print("\nPreview of first 10 rows:\n")
print(df_roadmap[["Research Domain", "Measurement (Plain English)", "W1", "W2", "W3", "W14", "W16"]].head(10).to_string(index=False))
