# decoders/panasonic.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Panasonic (Kaseikyo) protocol fields.
    Payload structure: 48 bits (6 Bytes: Manufacturer(2), System, Device, Command, Checksum).
    """
    # A full Panasonic transmission requires at least 99 data points (Header + 48 bits + Stop Mark)
    if len(pulses) < 98:
        return {"status": "Error", "message": "Signal too short for Panasonic"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (3456µs mark, 1728µs space)
    if not (is_tol(pulses[0], 3456) and is_tol(pulses[1], 1728)):
        return {"status": "Error", "message": "Invalid Panasonic Header"}

    bits = []
    
    # 2. Bit Extraction
    for i in range(2, 98, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # Mark should be ~432µs
        if not is_tol(mark, 432):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 432):
            bits.append(0)
        elif is_tol(space, 1296):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 3. Payload Parsing (LSB First per byte)
    bytes_arr = []
    for i in range(0, 48, 8):
        byte_bits = bits[i:i+8]
        byte_bits.reverse()  # Reverse to read LSB first correctly
        bytes_arr.append(int("".join(map(str, byte_bits)), 2))

    # 4. Field Assignment
    # Panasonic groups the 48 bits into 6 standard bytes
    manufacturer_val = (bytes_arr[0] << 8) | bytes_arr[1]
    system_val = bytes_arr[2]
    device_val = bytes_arr[3]
    command_val = bytes_arr[4]
    checksum_val = bytes_arr[5]

    # Optional: We can validate the checksum (usually XOR of bytes 2, 3, and 4)
    # However, some OEM variants modify the checksum rule, so reporting the value is safer.

    return {
        "status": "Success",
        "protocol": "Panasonic",
        "manufacturer_code": hex(manufacturer_val),
        "system": hex(system_val),
        "device": hex(device_val),
        "command": hex(command_val),
        "checksum": hex(checksum_val)
    }