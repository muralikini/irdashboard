# decoders/nec.py

def decode(pulses, tolerance=0.20):
    """Decodes mark/space timings into NEC protocol fields."""
    if len(pulses) < 67:
        return {"status": "Error", "message": "Signal too short for NEC"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation
    if not (is_tol(pulses[0], 9000) and is_tol(pulses[1], 4500)):
        # Check for repeat code
        if is_tol(pulses[0], 9000) and is_tol(pulses[1], 2250):
             return {"status": "Repeat", "message": "NEC Repeat Code Detected"}
        return {"status": "Error", "message": "Invalid Header"}

    # 2. Bit Extraction
    bits = []
    for i in range(2, 66, 2):
        space = pulses[i+1]
        if is_tol(space, 560):
            bits.append(0)
        elif is_tol(space, 1690):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 3. Byte Assembly (LSB First)
    bytes_arr = []
    for i in range(0, 32, 8):
        byte_bits = bits[i:i+8]
        byte_bits.reverse()
        bytes_arr.append(int("".join(map(str, byte_bits)), 2))

    address, address_inv, command, command_inv = bytes_arr

    # Note: Checksum validation (address + address_inv == 255) can be added here
    # depending on how strict you want the parser to be before it attempts "Extended NEC".

    return {
        "status": "Success",
        "protocol": "NEC",
        "address": hex(address),
        "command": hex(command)
    }