# encoders/zenith.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Zenith 22-bit protocol fields into a Mark/Space timing array."""
    
    # 1. Determine the 22-bit payload value
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0x3FFFFF
    else:
        addr = int(str(address_hex), 16) & 0xFF if address_hex else 0x00
        cmd = int(str(command_hex), 16) & 0x3FFF if command_hex else 0x00
        payload = (addr << 14) | cmd

    # 2. Extract bits (22 bits, MSB first)
    bits = [(payload >> i) & 1 for i in range(21, -1, -1)]

    # 3. Convert logical bits to Microsecond Pulses
    pulses = []
    
    # Zenith does not use a header pulse; it starts directly with data[cite: 19]
    for bit in bits:
        pulses.append(520)  # Mark is always ~520µs[cite: 19]
        pulses.append(1040 if bit == 1 else 520)  # Space: 1040µs for '1', 520µs for '0'[cite: 19]

    # Append final stop mark to terminate the sequence
    pulses.append(520)

    return pulses