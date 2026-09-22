import pyreadstat
import json

dta_path = "/home/abdulmohib/Downloads/randhrs1992_2022v1_STATA/randhrs1992_2022v1.dta"
catalog_path = "variable_catalog.json"

print("Extracting metadata and variable labels for all 19,880 variables...")
_, meta = pyreadstat.read_dta(dta_path, metadataonly=True)

# Build a dictionary mapping variable code -> full English label
catalog = {}
for var_name, var_label in meta.column_names_to_labels.items():
    var_lower = var_name.lower()
    label_text = var_label.strip() if var_label else "No description available"
    catalog[var_lower] = label_text

with open(catalog_path, "w") as f:
    json.dump(catalog, f, indent=2)

print(f"Catalog complete! Saved {len(catalog):,} variable definitions to {catalog_path}")
