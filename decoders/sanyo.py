# decoders/sanyo.py

def decode(pulses, tolerance=0.20):
    """
    Decodes mark/space timings into the Sanyo IR protocol (NEC 42-bit variant).
    Payload structure: 42 bits (13-bit Address, 13-bit Address Inv, 8-bit Cmd, 8-bit Cmd Inv).
    """
    if len(pulses) < 87:
        return {"status": "Error", "message": "Signal too short for Sanyo"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Header Validation (9000µs mark, 4500µs space)
    if not (is_tol(pulses[0], 9000) and is_tol(pulses[1], 4500)):
        if is_tol(pulses[0], 9000) and is_tol(pulses[1], 2250):
             return {"status": "Repeat", "message": "Sanyo Repeat Code Detected"}
        return {"status": "Error", "message": "Invalid Sanyo Header"}

    bits = []
    
    # Extract the 42 bits
    for i in range(2, 86, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        if not is_tol(mark, 560):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 560):
            bits.append(0)
        elif is_tol(space, 1690):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # Reverse to read LSB first
    bits.reverse()
    payload_val = int("".join(map(str, bits)), 2)

    return {
        "status": "Success",
        "protocol": "Sanyo (42-bit)",
        "payload": hex(payload_val)
    }