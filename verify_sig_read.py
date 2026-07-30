# verify_sig_read.py
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

    raw_words = []
    for i in range(0, len(content) - 1, 2):
        val = struct.unpack("<H", content[i:i+2])[0]
        raw_words.append(val)

    # Extract raw timing components and reconstruct bursts
    # In these .SIG files, small values represent sub-bursts or carrier cycles.
    # Let's accumulate consecutive small values or filter by the exact mask.
    masked_timings = [val & 0xFFFF for val in raw_words]

    # Reconstruct continuous bursts by grouping values below a carrier threshold
    demodulated = []
    current_burst = 0
    
    for t in masked_timings:
        # If the value is very large, it represents a space or a header boundary
        if t > 2500:
            if current_burst > 0:
                demodulated.append(current_burst)
                current_burst = 0
            demodulated.append(t)
        else:
            current_burst += t

    if current_burst > 0:
        demodulated.append(current_burst)

    print(f"Reconstructed pulse count: {len(demodulated)}")
    print("\nFirst 20 reconstructed pulses (looking for ~9017, ~4514):")
    print(demodulated[:20])

if __name__ == "__main__":
    main()