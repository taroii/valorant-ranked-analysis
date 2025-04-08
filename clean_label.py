import re
import pandas as pd

def clean_label(label):
    # Strip, remove spaces around slashes, then replace remaining spaces with _
    label = label.strip()
    label = re.sub(r"\s*/\s*", "/", label)         # Turn " / " into "/"
    label = re.sub(r"\s+", "_", label)             # Turn all spaces into underscores
    label = re.sub(r"[^\w/]+", "_", label)         # Replace any other symbols (like : or ,) with _
    label = label.strip("_")                       # Remove leading/trailing underscores
    return label.lower()                           # Optional: lowercase everything

def standardize_column_name(col):
    # Lowercase
    col = col.lower()

    # Replace symbols and normalize
    col = col.replace(" ", "_")
    col = col.replace("/", "_per_")
    col = col.replace("-", "_")
    col = col.replace("δ", "delta")
    col = col.replace("±", "delta")  
    col = col.replace("%", "percent")

    # Remove duplicate underscores
    col = re.sub(r"__+", "_", col)

    # Remove trailing underscores
    col = col.strip("_")

    return col

def standardize_column_names(df):
    df.columns = [standardize_column_name(col) for col in df.columns]
    return df

def time_to_seconds(time_str):
    if pd.isnull(time_str):
        return None
    match = re.match(r"(?:(\d+)m)? ?(?:(\d+)s)?", time_str.strip())
    if not match:
        return None
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2)) if match.group(2) else 0
    return minutes * 60 + seconds

def clean_numeric_column(series):
    if series.dtype != object:
        return series  # already numeric, return as-is

    non_null = series.dropna().astype(str)

    has_percent = non_null.str.contains("%").any()
    has_comma = non_null.str.contains(",").any()
    
    if has_comma:
        non_null = non_null.str.replace(",", "", regex=False)
    if has_percent:
        non_null = non_null.str.replace("%", "", regex=False)
        return pd.to_numeric(non_null, errors="coerce") / 100

    return pd.to_numeric(non_null, errors="coerce")

