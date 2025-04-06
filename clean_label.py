import re

def clean_label(label):
    # Strip, remove spaces around slashes, then replace remaining spaces with _
    label = label.strip()
    label = re.sub(r"\s*/\s*", "/", label)         # Turn " / " into "/"
    label = re.sub(r"\s+", "_", label)             # Turn all spaces into underscores
    label = re.sub(r"[^\w/]+", "_", label)         # Replace any other symbols (like : or ,) with _
    label = label.strip("_")                       # Remove leading/trailing underscores
    return label.lower()                           # Optional: lowercase everything