# decoders/sony.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Sony SIRC protocol fields.
    Handles 12-bit, 15-bit, and 20-bit payload structures.
    """
    # Minimum pulses for a 12-bit signal: Header (2) + 12 bits (24 max, or 23 if last space is dropped)
    if len(pulses) < 23:
        return {"status": "Error", "message": "Signal too short for Sony SIRC"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (2400µs mark, 600µs space)
    if not (is_tol(pulses[0], 2400) and is_tol(pulses[1], 600)):
        return {"status": "Error", "message": "Invalid Sony SIRC Header"}

    bits = []
    
    # 2. Extract Bits (Pulse Width Modulation)
    # Iterate through the remaining pulses to extract marks and spaces
    for i in range(2, len(pulses)):
        if i % 2 == 0:  
            # Even index = Mark
            mark = pulses[i]
            if is_tol(mark, 600):
                bits.append(0)
            elif is_tol(mark, 1200):
                bits.append(1)
            else:
                break # Invalid mark length or end of valid frame
        else:  
            # Odd index = Space
            space = pulses[i]
            if not is_tol(space, 600):
                # SIRC spaces are strictly 600µs. If it deviates, the frame is over.
                break

    # 3. Payload Validation
    if len(bits) not in [12, 15, 20]:
        return {"status": "Error", "message": f"Invalid Sony SIRC bit count: {len(bits)}"}

    # 4. Parsing (LSB First)
    # The Command is always the first 7 bits across all SIRC versions
    command_bits = bits[0:7]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    result = {
        "status": "Success",
        "protocol": f"Sony SIRC {len(bits)}-bit",
        "command": hex(command_val)
    }

    # Extract Address/Extended depending on version
    if len(bits) == 12:
        address_bits = bits[7:12]
        address_bits.reverse()
        result["address"] = hex(int("".join(map(str, address_bits)), 2))
        
    elif len(bits) == 15:
        address_bits = bits[7:15]
        address_bits.reverse()
        result["address"] = hex(int("".join(map(str, address_bits)), 2))
        
    elif len(bits) == 20:
        address_bits = bits[7:12]
        address_bits.reverse()
        result["address"] = hex(int("".join(map(str, address_bits)), 2))
        
        extended_bits = bits[12:20]
        extended_bits.reverse()
        result["extended"] = hex(int("".join(map(str, extended_bits)), 2))

    return result