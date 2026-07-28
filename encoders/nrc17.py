# encoders/nrc17.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Nokia NRC17 protocol fields into a Mark/Space timing array."""
    
    # 1. Parse fields (Command: 8-bit, Address: 4-bit, Subcode: 4-bit)
    cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0x00
    addr = int(str(address_hex), 16) & 0xF if address_hex else 0x0
    
    # Payload handles the Subcode if specified separately, otherwise default to 0x0
    subcode = int(str(payload_hex), 16) & 0xF if payload_hex else 0x0

    # 2. Construct the 17 logical bits (LSB first for data fields)
    start_bit = 1
    
    # Extract bits LSB first
    cmd_bits = [(cmd >> i) & 1 for i in range(8)]
    addr_bits = [(addr >> i) & 1 for i in range(4)]
    sub_bits = [(subcode >> i) & 1 for i in range(4)]
    
    logical_bits = [start_bit] + cmd_bits + addr_bits + sub_bits

    # 3. Manchester Encoding (Logical 1 -> Mark/Space [1, 0]; Logical 0 -> Space/Mark [0, 1])
    half_bits = []
    for bit in logical_bits:
        if bit == 1:
            half_bits.extend([1, 0])
        else:
            half_bits.extend([0, 1])

    # 4. Convert half-bits to Microsecond Pulses
    T = 500  # Base half-bit duration in microseconds
    
    # NRC17 Header: 500µs mark, 2500µs space
    pulses = [1 * T, 5 * T]
    
    current_level = 1  # State after the header space is a Mark
    duration = 0

    for hb in half_bits:
        if hb == current_level:
            duration += T
        else:
            pulses.append(duration)
            current_level = hb
            duration = T

    # Append final duration block
    pulses.append(duration)

    return pulses