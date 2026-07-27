# legacy_parser.py
import os
from itertools import groupby

def parse_legacy_file(filepath):
    """
    Parses raw binary .U1 (633 kHz) or .U2 (1 MHz) files 
    into a flat list of microsecond durations [mark, space, mark, space...].
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        if not data:
            return []

        # Determine the microsecond multiplier based on the file extension
        ext = os.path.splitext(filepath)[1].upper()
        if ext == '.U1':
            us_per_sample = 1000000.0 / 633000.0  # ~1.579 microseconds per bit
        elif ext == '.U2':
            us_per_sample = 1.0                   # 1.0 microsecond per bit
        else:
            return [] # Unsupported file type

        # Convert bytes to a continuous string of '0's and '1's (MSB first)
        bit_string = ''.join(f'{byte:08b}' for byte in data)

        raw_durations = []
        
        # Group consecutive identical bits and calculate their microsecond duration
        for state, group in groupby(bit_string):
            bit_count = sum(1 for _ in group)
            duration_us = int(round(bit_count * us_per_sample))
            raw_durations.append((int(state), duration_us))

        if not raw_durations:
            return []

        # The idle state is almost always the one with the longest single duration (silence)
        longest_duration = max(raw_durations, key=lambda x: x[1])
        idle_state = longest_duration[0]
        active_state = 1 if idle_state == 0 else 0

        # Envelope Detector: Bridge carrier gaps
        flat_durations = []
        in_mark = False
        current_mark = 0
        current_space = 0

        for state, duration in raw_durations:
            if state == active_state:
                if not in_mark:
                    in_mark = True
                    if current_space > 0:
                        flat_durations.append(current_space)
                    current_mark = duration
                else:
                    current_mark += duration
            else: # state == idle_state
                if duration < 150 and in_mark: # Bridge carrier gaps
                    current_mark += duration
                else:
                    if in_mark:
                        flat_durations.append(current_mark)
                        in_mark = False
                        current_space = duration
                    else:
                        current_space += duration
                        
        if in_mark:
            flat_durations.append(current_mark)

        # --- THE FIX: Clean up leading noise and silence ---
        # A valid IR starting mark is rarely under 150us and never over 20,000us.
        # By popping invalid starting values, we naturally resynchronize the Mark/Space alternating pattern.
        while len(flat_durations) > 0:
            if flat_durations[0] > 20000 or flat_durations[0] < 150:
                flat_durations.pop(0)
            else:
                break

        if not flat_durations:
            return []

        # If there's an odd number of elements (a Mark without a following Space), 
        # add a large dummy space so decoders don't throw an IndexError.
        if len(flat_durations) % 2 != 0:
            flat_durations.append(100000) 

        # Return the FLAT LIST directly!
        return flat_durations

    except Exception as e:
        print(f"Error parsing legacy file {filepath}: {e}")
        return []