# decoders/bo.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into the Bang & Olufsen (455 kHz) protocol.
    Typically a 16-bit payload.
    """
    # A standard B&O frame needs at least 33 data points (16 bits + trailer)
    if len(pulses) < 33:
        return {"status": "Error", "message": "Signal too short for B&O"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    bits = []
    
    # Check the pulse-distance modulation
    for i in range(0, 32, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # B&O marks are always 200µs
        if not is_tol(mark, 200):
            return {"status": "Error", "message": f"Invalid B&O Mark at index {i}"}
            
        if is_tol(space, 3125):
            bits.append(0)
        elif is_tol(space, 6250):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid B&O Space at index {i+1}"}

    # Standard B&O transmits MSB first
    payload_val = int("".join(map(str, bits)), 2)

    return {
        "status": "Success",
        "protocol": "Bang & Olufsen (455 kHz)",
        "payload": hex(payload_val)
    }