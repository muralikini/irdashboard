# read_sig_binary_marks.py
import os
import struct

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "AC_Captures", "AC129", "639107477229169738.SIG")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "rb") as f:
        content = f.read()

    print(f"Total file size: {len(content)} bytes")
    
    # 1. Print Binary Representation (First 500 bytes to keep it readable)
    binary_representation = "".join(format(b, '08b') for b in content[:500])
    print("\n--- First 500 bytes converted to 0s and 1s (8 bits per byte) ---")
    chunks = [binary_representation[i:i+32] for i in range(0, len(binary_representation), 32)]
    for chunk in chunks[:15]:
        print(" ".join(chunk[j:j+8] for j in range(0, len(chunk), 8)))

    # 2. Extract Mark / Space Sequence by parsing 16-bit little-endian words
    raw_words = []
    for i in range(0, len(content) - 1, 2):
        val = struct.unpack("<H", content[i:i+2])[0]
        raw_words.append(val)

    # Clean and isolate timing values to map out the exact Mark and Space sequence
    # Filtering out high-frequency framing noise to reveal the true durations
    clean_timings = [w for w in raw_words if 100 <= w <= 20000]

    print("\n--- Reconstructed Mark / Space Timing Sequence (First 30 elements) ---")
    print(clean_timings[:30])

if __name__ == "__main__":
    main()