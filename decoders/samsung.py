# decoders/samsung.py

def decode(pulses, tolerance=0.30): 
    """Decodes mark/space timings into Samsung or 32-bit RCA variant fields."""
    
    if len(pulses) < 66:
        return {"status": "Error", "message": "Signal too short for 32-bit protocol"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Accept standard 4500/4500 OR the legacy 4000/4000 stretched variant
    if not ((is_tol(pulses[0], 4500) or is_tol(pulses[0], 4000)) and 
            (is_tol(pulses[1], 4500) or is_tol(pulses[1], 4000))):
        return {"status": "Error", "message": "Invalid Header"}

    bits = []
    
    # Extract the 32 bits
    for i in range(2, 66, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Marks are usually ~500-560
        if not is_tol(mark, 560):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        # Space 0 is usually 560, but stretched to ~850 in legacy hardware
        if is_tol(space, 560) or is_tol(space, 850):
            bits.append(0)
        # Space 1 is usually 1690, but stretched to ~2000 in legacy hardware
        elif is_tol(space, 1690) or is_tol(space, 2000):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # Reverse bits (LSB first) and convert to hex
    bits.reverse()
    payload_val = int("".join(map(str, bits)), 2)

    return {
        "status": "Success",
        "protocol": "Samsung/RCA-32 Variant",
        "payload": hex(payload_val)
    }