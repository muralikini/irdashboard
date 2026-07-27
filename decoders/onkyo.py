# decoders/onkyo.py

def decode(pulses, tolerance=0.20):
    """
    Decodes mark/space timings into Onkyo protocol fields.
    Payload structure: 32 bits total (16-bit Address, 16-bit Command).
    """
    # A full transmission requires at least 67 data points (Header + 32 bits + Stop Mark)
    if len(pulses) < 67:
        return {"status": "Error", "message": "Signal too short for Onkyo"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (9000µs mark, 4500µs space)
    if not (is_tol(pulses[0], 9000) and is_tol(pulses[1], 4500)):
        if is_tol(pulses[0], 9000) and is_tol(pulses[1], 2250):
             return {"status": "Repeat", "message": "Onkyo Repeat Code Detected"}
        return {"status": "Error", "message": "Invalid Onkyo Header"}

    bits = []
    
    # 2. Bit Extraction
    for i in range(2, 66, 2):
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

    # 3. Payload Parsing (LSB First per 8-bit byte)
    bytes_arr = []
    for i in range(0, 32, 8):
        byte_bits = bits[i:i+8]
        byte_bits.reverse()  # Reverse to read LSB first correctly
        bytes_arr.append(int("".join(map(str, byte_bits)), 2))

    # 4. Assemble 16-bit blocks
    # Onkyo uses bytes 0 and 1 for the Address, and bytes 2 and 3 for the Command
    address_val = (bytes_arr[0] << 8) | bytes_arr[1]
    command_val = (bytes_arr[2] << 8) | bytes_arr[3]

    return {
        "status": "Success",
        "protocol": "Onkyo",
        "address": hex(address_val),
        "command": hex(command_val)
    }