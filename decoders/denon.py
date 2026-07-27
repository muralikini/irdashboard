# decoders/denon.py

def decode(pulses, tolerance=0.30):
    """
    Decodes mark/space timings into Denon protocol fields.
    Payload structure: 15 bits total (5 Address, 10 Command).
    """
    # A single Denon transmission requires at least 31 data points (15 bits + Stop Mark)
    if len(pulses) < 31:
        return {"status": "Error", "message": "Signal too short for Denon"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Denon does NOT have a header. 
    # If the first pulse is massive (like NEC's 9000µs or RCA's 4000µs), it is not Denon.
    if pulses[0] > 1000:
        return {"status": "Error", "message": "Invalid Denon Mark (Header detected)"}

    bits = []
    
    # Extract the 15 payload bits
    for i in range(0, 30, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Mark should be ~275µs.
        if not is_tol(mark, 275):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 775):
            bits.append(0)
        elif is_tol(space, 1900):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 1. Payload Parsing (LSB First)
    
    # 5-bit Address
    address_bits = bits[0:5]
    address_bits.reverse()
    address_val = int("".join(map(str, address_bits)), 2)

    # 10-bit Command
    command_bits = bits[5:15]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    return {
        "status": "Success",
        "protocol": "Denon",
        "address": hex(address_val),
        "command": hex(command_val)
    }