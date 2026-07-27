# decoders/kaseikyo.py

def decode(pulses, tolerance=0.30):
    """
    Decodes mark/space timings into the Generic Kaseikyo protocol.
    Payload structure: 48 bits.
    """
    if len(pulses) < 99:
        return {"status": "Error", "message": "Signal too short for Kaseikyo"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Header Validation: 3456µs mark, 1728µs space
    if not (is_tol(pulses[0], 3456) and is_tol(pulses[1], 1728)):
        return {"status": "Error", "message": "Invalid Kaseikyo Header"}

    bits = []
    
    # Extract the 48 bits
    for i in range(2, 98, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        if not is_tol(mark, 432):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 432):
            bits.append(0)
        elif is_tol(space, 1296):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # Kaseikyo transmits LSB first
    bits.reverse()
    payload_val = int("".join(map(str, bits)), 2)

    return {
        "status": "Success",
        "protocol": "Kaseikyo (Generic)",
        "payload": hex(payload_val)
    }