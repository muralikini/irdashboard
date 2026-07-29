# decoders/nec.py

def decode(pulses, tolerance=0.20):
    """Decodes single or multi-frame mark/space timings into NEC protocol fields."""
    if len(pulses) < 4:
        return {"status": "Error", "message": "Signal too short for NEC"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # Check for direct repeat code frame
    if is_tol(pulses[0], 9000) and is_tol(pulses[1], 2250):
        return {
            "status": "Repeat",
            "protocol": "NEC",
            "message": "NEC Repeat Frame Detected",
            "header_mark": pulses[0],
            "header_space": pulses[1]
        }

    # Standard 32-bit Frame Validation (requires 67 transitions: 1 header + 64 data + 1 stop mark)
    if len(pulses) < 67:
        return {"status": "Error", "message": "Signal too short for standard NEC data frame"}

    # 1. Header Validation
    if not (is_tol(pulses[0], 9000) and is_tol(pulses[1], 4500)):
        return {"status": "Error", "message": "Invalid NEC Header"}

    # 2. Bit Extraction
    bits = []
    for i in range(2, 66, 2):
        if i + 1 >= len(pulses):
            break
        space = pulses[i+1]
        if is_tol(space, 560):
            bits.append(0)
        elif is_tol(space, 1690):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}: {space}µs"}

    if len(bits) < 32:
        return {"status": "Error", "message": "Incomplete NEC data bits extracted"}

    # 3. Byte Assembly (LSB First)
    bytes_arr = []
    for i in range(0, 32, 8):
        byte_bits = bits[i:i+8]
        byte_bits.reverse()
        bytes_arr.append(int("".join(map(str, byte_bits)), 2))

    address, address_inv, command, command_inv = bytes_arr

    return {
        "status": "Success",
        "protocol": "NEC",
        "address": hex(address),
        "command": hex(command),
        "extended": hex(address) if address > 255 else None
    }