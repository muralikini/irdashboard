# decoders/jvc.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into JVC protocol fields.
    Payload structure: 16 bits (8 Address, 8 Command).
    """
    # A full JVC transmission with header requires at least 35 data points (Header + 16 bits + Stop Mark)
    if len(pulses) < 35:
        return {"status": "Error", "message": "Signal too short for JVC"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (8416µs mark, 4208µs space)
    if not (is_tol(pulses[0], 8416) and is_tol(pulses[1], 4208)):
        # Note: Repeated JVC signals lack a header, but for initial key mapping, 
        # we expect the clean initial press containing the header.
        return {"status": "Error", "message": "Invalid JVC Header"}

    bits = []
    
    # 2. Bit Extraction
    for i in range(2, 34, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Mark should be ~526µs
        if not is_tol(mark, 526):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 526):
            bits.append(0)
        elif is_tol(space, 1578):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 3. Payload Parsing (LSB First)
    
    # 8-bit Address
    address_bits = bits[0:8]
    address_bits.reverse()
    address_val = int("".join(map(str, address_bits)), 2)

    # 8-bit Command
    command_bits = bits[8:16]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    return {
        "status": "Success",
        "protocol": "JVC",
        "address": hex(address_val),
        "command": hex(command_val)
    }