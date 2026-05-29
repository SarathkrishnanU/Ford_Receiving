import pandas as pd
import numpy as np

file_path = r"C:\Users\skrishnan1\Videos\Proj\Item_Trend_with_Spikes.xlsx"
df = pd.read_excel(file_path)

# Exclude Grand Total column safely
numeric_cols = []
for col in df.select_dtypes(include=[np.number]).columns:
    col_str = str(col).lower()
    if "total" not in col_str:
        numeric_cols.append(col)

def classify_trend(values):
    if len(values) < 2:
        return "Stable"
    x = np.arange(len(values))
    values = np.asarray(values, dtype=float)
    slope = np.polyfit(x, values, 1)[0]
    if slope > 0:
        return "Increasing"
    elif slope < 0:
        return "Decreasing"
    return "Stable"

def detect_spike(values):
    if len(values) < 3:
        return False
    mean = np.mean(values)
    for i in range(1, len(values)-1):
        v = values[i]
        if mean != 0 and abs(v - mean) / abs(mean) > 0.3:
            if abs(v - values[i-1]) > 0.3*abs(mean) and abs(v - values[i+1]) > 0.3*abs(mean):
                return True
    return False

trends = []
for _, row in df.iterrows():
    vals = row[numeric_cols].dropna().values
    trend = classify_trend(vals)
    if detect_spike(vals):
        trend += " + Spike"
    trends.append(trend)

df["Trend"] = trends

output_path = r"C:\Users\skrishnan1\Videos\Proj\Final_Item_Trend.xlsx"
df.to_excel(output_path, index=False)

output_path
