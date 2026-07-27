# decoders/rca.py

def decode(pulses, tolerance=0.20):
    """
    Decodes mark/space timings into RCA protocol fields.
    Payload structure: 24 bits total (4 Address, 8 Command, 4 Inv Address, 8 Inv Command).
    """
    # A full RCA transmission requires at least 51 data points (Header + 24 bits + Stop)
    if len(pulses) < 51:
        return {"status": "Error", "message": "Signal too short for RCA"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (4000µs mark, 4000µs space)
    if not (is_tol(pulses[0], 4000) and is_tol(pulses[1], 4000)):
        return {"status": "Error", "message": "Invalid RCA Header"}

    # 2. Bit Extraction
    bits = []
    for i in range(2, 50, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        if not is_tol(mark, 500):
            return {"status": "Error", "message": f"Invalid Bit Mark at index {i}"}
            
        if is_tol(space, 1000):
            bits.append(0)
        elif is_tol(space, 2000):
            bits.append(1)
        else:
            return {"status": "Error", "message": f"Invalid Space duration at index {i+1}"}

    # 3. Payload Parsing
    # RCA protocol transmits the 4-bit Address MSB first
    address_bits = bits[0:4]
    address_val = int("".join(map(str, address_bits)), 2)

    # The 8-bit Command is transmitted LSB first, so we reverse it
    command_bits = bits[4:12]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    # 4. Optional Checksum Validation
    inv_address_bits = bits[12:16]
    inv_command_bits = bits[16:24]
    inv_command_bits.reverse()
    
    inv_address_val = int("".join(map(str, inv_address_bits)), 2)
    inv_command_val = int("".join(map(str, inv_command_bits)), 2)
    
    # Address + Inv Address for 4 bits is 15 (0xF)
    if (address_val + inv_address_val) != 15:
         return {"status": "Error", "message": "Address Checksum Failed"}
         
    # Command + Inv Command for 8 bits is 255 (0xFF)
    if (command_val + inv_command_val) != 255:
         return {"status": "Error", "message": "Command Checksum Failed"}

    return {
        "status": "Success",
        "protocol": "RCA",
        "address": hex(address_val),
        "command": hex(command_val)
    }