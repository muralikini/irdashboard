# decoders/rc6.py

def decode(pulses, tolerance=0.30):
    """
    Decodes mark/space timings into the RC6 protocol.
    """
    T = 444  # Base time unit for RC6 is ~444 microseconds
    
    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    if len(pulses) < 20:
        return {"status": "Error", "message": "Signal too short for RC6"}

    # 1. Header Validation: ~2666µs mark, ~889µs space (6T, 2T)
    if not (is_tol(pulses[0], 6 * T) and is_tol(pulses[1], 2 * T)):
        return {"status": "Error", "message": "Invalid RC6 Header"}

    # 2. Extract ONLY the first frame (stop at the large gap between repeats)
    frame_pulses = []
    for p in pulses[2:]:
        if p > 10000:  # A gap larger than 10ms means the frame is over
            break
        frame_pulses.append(p)

    # 3. Convert physical pulses to T-units
    t_units = []
    state = 1  # Starts with a Mark (1)
    for p in frame_pulses:
        if is_tol(p, T):
            t_units.append(state)
        elif is_tol(p, 2 * T):
            t_units.extend([state, state])
        elif is_tol(p, 3 * T):
            t_units.extend([state, state, state])
        else:
            return {"status": "Error", "message": f"Invalid pulse length {p}µs"}
        state = 1 - state  # Alternate between Mark (1) and Space (0)

    # 4. Decode Manchester (1->0 transition is a '1', 0->1 transition is a '0')
    bits = []
    i = 0
    bit_count = 0
    
    while i < len(t_units) - 1:
        # The Toggle bit (4th bit) is twice as long in RC6 (2T per half)
        if bit_count == 4:
            if i + 3 >= len(t_units): break
            first_half = t_units[i]
            second_half = t_units[i+2]
            i += 4
        else:
            first_half = t_units[i]
            second_half = t_units[i+1]
            i += 2
        
        if first_half == 1 and second_half == 0:
            bits.append(1)
        elif first_half == 0 and second_half == 1:
            bits.append(0)
        else:
            return {"status": "Error", "message": "Manchester transition error"}
        
        bit_count += 1
        if bit_count == 21:  # Standard RC6 Mode 0 has 21 bits total
            break

    if len(bits) < 21:
        return {"status": "Error", "message": f"Incomplete payload, got {len(bits)} bits"}

    # Skip start (1 bit), mode (3 bits), and toggle (1 bit). Read the 16 data bits.
    payload_val = int("".join(map(str, bits[5:])), 2)

    return {
        "status": "Success",
        "protocol": "RC6",
        "payload": hex(payload_val)
    }