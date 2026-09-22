import pandas as pd

# Load the already generated CSV
df = pd.read_csv("randhrs_complete_roadmap_all_waves.csv")

# Set display width for terminal viewing
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 100)

print("="*120)
print("RAND HRS COMPLETE ROADMAP: ALL 16 WAVES ACROSS ALL MEASUREMENTS & DOMAINS")
print("="*120)

# Display Landmark Waves in Terminal
preview_cols = ["Research Domain", "Measurement (Plain English)", "Variable Pattern", "R1", "R2", "R3", "R8", "R14", "R16"]
print(df[preview_cols].to_string(index=False))

# Also export directly to Excel (.xlsx) if openpyxl is installed
try:
    df.to_excel("randhrs_complete_roadmap_all_waves.xlsx", index=False)
    print("\nSaved native Excel workbook: randhrs_complete_roadmap_all_waves.xlsx")
except Exception:
    pass

print("\nFull CSV with all 16 waves is ready: randhrs_complete_roadmap_all_waves.csv")
