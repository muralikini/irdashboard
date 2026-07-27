# decoders/zenith.py

def decode(pulses, tolerance=0.30):
    """
    Decodes mark/space timings into Zenith protocol fields.
    Payload structure: 22 bits. No header.
    """
    # A single Zenith transmission requires 45 data points (22 bits + Stop Mark)
    if len(pulses) < 45:
        return {"status": "Error", "message": "Signal too short for Zenith"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Zenith does NOT have a header. 
    # Check for massive header pulses to fail fast.
    if pulses[0] > 1000:
        return {"status": "Error", "message": "Invalid Zenith Mark (Header detected)"}

    bits = []
    
    # Extract the 22 payload bits
    for i in range(0, 44, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Mark should be ~520µs.
        if not is_tol(mark, 520):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 520):
            bits.append(0)
        elif is_tol(space, 1040):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    payload_val = int("".join(map(str, bits)), 2)

    return {
        "status": "Success",
        "protocol": "Zenith",
        "payload": hex(payload_val)
    }