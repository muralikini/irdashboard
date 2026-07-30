# run_decoders.py
import os
import json
from decoders.decoder_registry import try_all_decoders

def parse_sig_file_to_pulses(file_path):
    """
    Loads a legacy .SIG file, normalizes encoding, and returns 
    the demodulated mark/space pulse array.
    """
    if not os.path.exists(file_path):
        return []

    raw_ordinals = []
    for enc in ["utf-16", "utf-16-le", "utf-16-be"]:
        try:
            with open(file_path, "r", encoding=enc, errors="ignore") as f:
                content = f.read()
            if content:
                raw_ordinals = [ord(c) for c in content]
                break
        except Exception:
            continue

    if not raw_ordinals:
        return []

    raw_timings = [val & 0xFFFF for val in raw_ordinals if 100 <= (val & 0xFFFF) <= 65000]
    
    # Carrier demodulation
    demodulated = []
    current_burst = 0
    threshold = 26.2 * 2.5

    for t in raw_timings:
        if t > threshold * 4:
            if current_burst > 0:
                demodulated.append(int(current_burst))
                current_burst = 0
            demodulated.append(int(t))
        else:
            current_burst += t

    if current_burst > 0:
        demodulated.append(int(current_burst))

    return demodulated

def execute_decoder_registry():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ac_dir = os.path.join(base_dir, "AC_Captures", "AC129")
    
    print("--- Running Decoder Registry on AC Captures ---")
    
    if not os.path.exists(ac_dir):
        print(f"Directory not found: {ac_dir}")
        return

    results = {}
    for filename in sorted(os.listdir(ac_dir)):
        if filename.upper().endswith('.SIG'):
            file_path = os.path.join(ac_dir, filename)
            
            # Get the clean pulse array
            pulses = parse_sig_file_to_pulses(file_path)
            
            if not pulses:
                results[filename] = {"status": "Failed to parse pulses"}
                continue

            # Pass directly into the project's decoder registry
            decoded_result = try_all_decoders(pulses)
            
            results[filename] = {
                "status": "Decoded" if decoded_result else "Unrecognized",
                "match_data": decoded_result
            }
            
            print(f"\nFile: {filename}")
            print(f"Decoder Result: {decoded_result}")

    # Save output match results
    output_path = os.path.join(base_dir, "AC_Captures", "ac_decoded_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    execute_decoder_registry()