# Health and Retirement Study (HRS) Longitudinal Explorer (1992–2022)

An interactive, high-performance research platform built with Streamlit and DuckDB to explore, visualize, and analyze the harmonized RAND HRS Longitudinal Dataset (Waves 1 to 16).

The dashboard maps complex longitudinal survey records into five core domains:
- Chronic Physical Health Conditions (Hypertension, Diabetes, Cancer, Stroke, Heart Disease)
- Memory & Cognitive Function (Immediate/Delayed Word Recall, Working Memory, Summary Scores)
- Mental Health & Health Behaviors (CES-D Depressive Scale, Smoking, Alcohol Consumption, Physical Activity)
- Physical Independence & Daily Living (ADLs, IADLs, Summary Limitations, BMI)
- Socioeconomic Status (SES) & Demographics (Income, Net Wealth, Labor Force, Household Composition)

---

## Architecture & Storage Design

- Zero-Setup Embedded Database: Uses DuckDB to query Parquet partitions directly from disk using in-memory columnar execution. No external database engines, daemons, or server configurations are needed.
- Modular Data Architecture (randhrs_parquet/): The original 2 GB Stata dataset has been partitioned into 33 modular Parquet files to eliminate memory bottlenecks on machines with standard hardware (e.g., 4GB–8GB RAM):
  - baseline_demographics.parquet: Invariant respondent demographics (ID, gender, education, race, birth cohort).
  - r1.parquet to r16.parquet: Primary respondent core interview records across all 16 survey waves.
  - s1.parquet to s16.parquet: Matched spouse/partner interview records across all 16 survey waves.
- Dynamic Variable Translation: variable_catalog.json translates raw Stata variable codes into human-readable RAND labels on the fly.
- Statistical Weighting: Supports dynamic toggling between unweighted sample metrics and US population-representative estimates via respondent wave weights (r*wtresp).

---

## Project Structure

.
├── app.py                         # Streamlit analytics application
├── variable_catalog.json          # Dictionary of 19,000+ Stata variable labels
├── requirements.txt               # Pinned Python package dependencies
├── README.md                      # Setup and usage guide
├── .gitignore                     # Git ignore rules for virtualenvs and raw data
└── randhrs_parquet/               # Modular partitioned dataset (33 files)
    ├── baseline_demographics.parquet
    ├── r1.parquet ... r16.parquet # Primary respondent waves (1992–2022)
    └── s1.parquet ... s16.parquet # Spouse/partner waves (1992–2022)

---

## Quick Start Guide

### Prerequisites
- Python 3.10 to 3.14 installed
- Git installed

---

### Setup for Linux & macOS

1. Clone the repository:
git clone https://github.com/abdulmohibbb/randhrs_research.git
cd randhrs_research

2. Create and activate a virtual environment:
python3 -m venv venv
source venv/bin/activate

3. Install dependencies:
pip install --upgrade pip
pip install -r requirements.txt

4. Run the dashboard:
streamlit run app.py

---

### Setup for Windows

1. Clone the repository:
Open Command Prompt (cmd) or PowerShell and run:
git clone https://github.com/abdulmohibbb/randhrs_research.git
cd randhrs_research

2. Create a virtual environment:
python -m venv venv

3. Activate the virtual environment:
- On Command Prompt (cmd.exe):
venv\Scripts\activate.bat

- On PowerShell:
.\venv\Scripts\Activate.ps1
(Note: If PowerShell throws an execution policy error, enable script execution for your session by running: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

4. Install dependencies:
python -m pip install --upgrade pip
pip install -r requirements.txt

5. Run the dashboard:
streamlit run app.py

---

## Accessing the Dashboard

Once started, Streamlit will automatically launch your default browser to:

http://localhost:8501

If it does not open automatically, open any browser and navigate to that address.

---

## Citation & Acknowledgments

- Health and Retirement Study (HRS): Sponsored by the National Institute on Aging (NIA U01AG009740, NIA R01AG073289) and the Social Security Administration, conducted by the University of Michigan.
- RAND HRS Longitudinal File (2022 V1): Produced by the RAND Center for the Study of Aging with funding from the NIA and SSA.
