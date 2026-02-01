import pandas as pd
import json

file_path = r"C:\Users\Yrving\WHAT_EVO_PRO\Reporte_Stock_BIEVO25_20260130.xlsx"

try:
    df = pd.read_excel(file_path, nrows=0)
    print(json.dumps(list(df.columns), indent=2))
except Exception as e:
    print(f"Error: {e}")
