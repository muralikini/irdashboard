# decoders/apple.py

def decode(pulses, tolerance=0.20):
    """
    Decodes mark/space timings into Apple IR protocol fields.
    Payload structure: 32 bits (Device ID 1, Device ID 2, Command, Pair ID).
    """
    # A full transmission requires at least 67 data points (Header + 32 bits + Stop Mark)
    if len(pulses) < 67:
        return {"status": "Error", "message": "Signal too short for Apple IR"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (9000µs mark, 4500µs space)
    if not (is_tol(pulses[0], 9000) and is_tol(pulses[1], 4500)):
        if is_tol(pulses[0], 9000) and is_tol(pulses[1], 2250):
             return {"status": "Repeat", "message": "Apple Repeat Code Detected"}
        return {"status": "Error", "message": "Invalid Apple Header"}

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
        byte_bits.reverse()
        bytes_arr.append(int("".join(map(str, byte_bits)), 2))

    device_id_1 = bytes_arr[0]
    device_id_2 = bytes_arr[1]
    command = bytes_arr[2]
    pair_id = bytes_arr[3]

    # 4. Apple Validation
    # Apple remotes typically use device IDs 224 (0xE0), 229 (0xE5), and 238 (0xEE)
    if device_id_1 not in [224, 229, 238]:
        return {"status": "Error", "message": "Device ID does not match Apple Protocol"}

    return {
        "status": "Success",
        "protocol": "Apple",
        "device_id_1": hex(device_id_1),
        "device_id_2": hex(device_id_2),
        "command": hex(command),
        "pair_id": hex(pair_id)
    }