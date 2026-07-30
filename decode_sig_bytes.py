# decode_sig_bytes.py
import os

sig_path = os.path.join("AC_Captures", "AC129", "639107476992368561.SIG")

if os.path.exists(sig_path):
    with open(sig_path, "r", encoding="utf-16") as f:
        text_content = f.read()
    
    # Convert characters back to their raw 16-bit code points (ordinals)
    code_points = [ord(c) for c in text_content[:200]]
    print("First 50 ordinal code points:")
    print(code_points[:50])