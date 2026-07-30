# inspect_headers.py
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "AC_Captures", "AC129", "639107476992368561.SIG")

raw_timings = []
if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-16", errors="ignore") as f:
        content = f.read()
        # Allow up to 20000 to catch the leading header mark
        for c in content:
            val = ord(c)
            if 100 <= val <= 20000:
                raw_timings.append(val)

print(f"Filtered valid samples: {len(raw_timings)}")
print(f"First 20 filtered samples: {raw_timings[:20]}")