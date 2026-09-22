import os
import re
from collections import defaultdict
import pyreadstat
import pyarrow as pa
import pyarrow.parquet as pq

dta_path = "/home/abdulmohib/Downloads/randhrs1992_2022v1_STATA/randhrs1992_2022v1.dta"
output_dir = "randhrs_parquet"
os.makedirs(output_dir, exist_ok=True)

print("Reading metadata across all 19,880 variables...")
_, meta = pyreadstat.read_dta(dta_path, metadataonly=True)
all_cols = meta.column_names

# Core identification and tracker variables
id_cols = [c for c in ["hhidpn", "hhid", "pn", "ragender", "raeduc", "raracem", "rahispan"] if c in all_cols]

# Partition into wave and domain groups
groups = defaultdict(list)
for col in all_cols:
    if col in id_cols:
        continue
    match = re.match(r"^([rs]\d{1,2})", col.lower())
    if match:
        groups[match.group(1)].append(col)
    else:
        groups["baseline_demographics"].append(col)

print(f"Split columns into {len(groups)} domain groups.")

# Process groups one by one in chunks of 5,000 rows
chunk_size = 5000

for grp_name, cols in sorted(groups.items()):
    target_cols = id_cols + cols
    out_file = os.path.join(output_dir, f"{grp_name}.parquet")
    print(f"\nProcessing {grp_name} ({len(target_cols)} columns)...")

    reader = pyreadstat.read_file_in_chunks(
        pyreadstat.read_dta,
        dta_path,
        chunksize=chunk_size,
        usecols=target_cols,
        apply_value_formats=False
    )

    writer = None

    for b_idx, (df, _) in enumerate(reader, start=1):
        # Cast any mixed object/string columns to clean string types
        # This resolves the 'Invalid null value' failure on radream5 and similar columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).replace({'nan': None, 'None': None, '<NA>': None})

        # Build arrow table directly without forcing a rigid prior schema
        table = pa.Table.from_pandas(df, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(out_file, table.schema, compression="snappy")

        # Align schemas by casting column-by-column to match the initial writer schema
        if table.schema != writer.schema:
            table = table.cast(writer.schema)

        writer.write_table(table)
        print(f"  Processed batch {b_idx}...", end="\r")

    if writer:
        writer.close()
    print(f"\n  Saved: {out_file}")

print(f"\nAll files converted successfully in '{output_dir}/'!")
