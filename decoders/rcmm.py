# decoders/rcmm.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Philips RC-MM protocol using Pulse Position Modulation.
    Payload lengths typically vary between 12, 24, and 32 bits.
    """
    # Requires at least a header and 6 data marks (12 bits)
    if len(pulses) < 15: 
        return {"status": "Error", "message": "Signal too short for RC-MM"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # RC-MM Header: 416µs Mark, 277µs Space
    if not (is_tol(pulses[0], 416) and is_tol(pulses[1], 277)):
        return {"status": "Error", "message": "Invalid RC-MM Header"}

    bits = []
    
    # Loop through pairs. RC-MM encodes 2 bits per space.
    for i in range(2, len(pulses) - 1, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # All data marks must be ~166µs. If not, the payload has ended.
        if not is_tol(mark, 166):
            break
            
        if is_tol(space, 277):
            bits.extend([0, 0])
        elif is_tol(space, 444):
            bits.extend([0, 1])
        elif is_tol(space, 611):
            bits.extend([1, 0])
        elif is_tol(space, 777):
            bits.extend([1, 1])
        else:
            break
            
    # Standard RC-MM bit lengths
    if len(bits) not in [12, 24, 32]:
        return {"status": "Error", "message": f"Incomplete RC-MM payload: {len(bits)} bits"}
        
    # RC-MM transmits MSB first, so we don't reverse the array
    payload_val = int("".join(map(str, bits)), 2) 
    
    return {
        "status": "Success",
        "protocol": f"RC-MM ({len(bits)}-bit)",
        "payload": hex(payload_val)
    }