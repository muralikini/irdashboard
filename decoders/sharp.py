# decoders/sharp.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Sharp protocol fields.
    Payload structure: 15 bits total (5 Address, 8 Command, 1 EXP, 1 CHK).
    """
    # A single Sharp transmission requires at least 31 data points (15 bits + Stop Mark)
    if len(pulses) < 31:
        return {"status": "Error", "message": "Signal too short for Sharp"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Sharp does NOT have a header. 
    # If the first pulse is massive (like NEC's 9000µs or RCA's 4000µs), it is not Sharp.
    if pulses[0] > 1000:
        return {"status": "Error", "message": "Invalid Sharp Mark (Header detected)"}

    bits = []
    # Extract the 15 payload bits
    for i in range(0, 30, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Mark should be ~320µs. (We use a slightly higher 25% tolerance here 
        # because hardware stretching on very short pulses is common).
        if not is_tol(mark, 320):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 680):
            bits.append(0)
        elif is_tol(space, 1680):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 1. Payload Parsing (LSB First)
    
    # 5-bit Address
    address_bits = bits[0:5]
    address_bits.reverse()
    address_val = int("".join(map(str, address_bits)), 2)

    # 8-bit Command
    command_bits = bits[5:13]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    # 2. Validation
    exp_bit = bits[13]
    chk_bit = bits[14]
    
    # The Check bit must be the inverted Expansion bit
    if exp_bit == chk_bit:
         return {"status": "Error", "message": "EXP and CHK bits do not match Sharp specs"}

    return {
        "status": "Success",
        "protocol": "Sharp",
        "address": hex(address_val),
        "command": hex(command_val),
        "exp": exp_bit,
        "chk": chk_bit
    }