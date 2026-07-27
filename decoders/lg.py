# decoders/lg.py

def decode(pulses, tolerance=0.20):
    """
    Decodes mark/space timings into LG protocol fields.
    Handles both 28-bit (Address + Command + Checksum) and 32-bit frames.
    """
    # Minimum pulses for a 28-bit signal: Header (2) + 28 bits (56) + Stop Mark (1) = 59
    if len(pulses) < 59:
        return {"status": "Error", "message": "Signal too short for LG"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation 
    # LG uses a 9000µs mark. The space can range from 2250µs to 4500µs depending on the variant.
    if not is_tol(pulses[0], 9000):
        return {"status": "Error", "message": "Invalid LG Header Mark"}
        
    # Check for valid spaces (4500µs standard, or ~4200µs)
    if not (is_tol(pulses[1], 4500) or is_tol(pulses[1], 4200)):
        # Check for repeat code (9000µs mark, 2250µs space)
        if is_tol(pulses[1], 2250):
             return {"status": "Repeat", "message": "LG Repeat Code Detected"}
        return {"status": "Error", "message": "Invalid LG Header Space"}

    bits = []
    
    # 2. Extract Bits (Pulse Distance Modulation)
    # Determine if we have enough pulses for 32 bits (67 data points) or 28 bits (59 data points)
    max_bits = 32 if len(pulses) >= 67 else 28
    max_pulses = (max_bits * 2) + 2
    
    for i in range(2, max_pulses, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        if not is_tol(mark, 560):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 560):
            bits.append(0)
        elif is_tol(space, 1680) or is_tol(space, 1600):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 3. Payload Parsing (LSB First)
    if len(bits) == 28:
        # LG 28-bit: 8-bit Address, 16-bit Command, 4-bit Checksum
        address_bits = bits[0:8]
        address_bits.reverse()
        address_val = int("".join(map(str, address_bits)), 2)
        
        command_bits = bits[8:24]
        command_bits.reverse()
        command_val = int("".join(map(str, command_bits)), 2)
        
        checksum_bits = bits[24:28]
        checksum_bits.reverse()
        checksum_val = int("".join(map(str, checksum_bits)), 2)
        
        return {
            "status": "Success",
            "protocol": "LG 28-bit",
            "address": hex(address_val),
            "command": hex(command_val),
            "checksum": hex(checksum_val)
        }
        
    elif len(bits) == 32:
        # LG 32-bit: Structurally similar to NEC (8-bit blocks)
        bytes_arr = []
        for i in range(0, 32, 8):
            byte_bits = bits[i:i+8]
            byte_bits.reverse()
            bytes_arr.append(int("".join(map(str, byte_bits)), 2))
            
        address = bytes_arr[0]
        address_inv = bytes_arr[1]
        command = bytes_arr[2]
        command_inv = bytes_arr[3]
        
        return {
            "status": "Success",
            "protocol": "LG 32-bit",
            "address": hex(address),
            "address_inv": hex(address_inv),
            "command": hex(command),
            "command_inv": hex(command_inv)
        }
        
    return {"status": "Error", "message": "Unknown LG bit length"}