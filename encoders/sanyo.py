# encoders/sanyo.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Sanyo (42-bit variant) protocol fields into a Mark/Space timing array."""
    
    # 1. Parse fields (13-bit Address and 8-bit Command)
    addr = int(str(address_hex), 16) & 0x1FFF if address_hex else 0x1F00
    cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0x50

    # If a custom 42-bit payload is directly provided, use it
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0x3FFFFFFFFFF
    else:
        # Construct the 42 bits: Address (13) + Inv Address (13) + Command (8) + Inv Command (8)
        addr_inv = (~addr) & 0x1FFF
        cmd_inv = (~cmd) & 0xFF
        
        payload = (addr << 29) | (addr_inv << 16) | (cmd << 8) | cmd_inv

    # 2. Extract bits (42 bits, LSB first since the decoder reverses them back)
    bits = [(payload >> i) & 1 for i in range(42)]

    # 3. Sanyo Header: 9000µs mark, 4500µs space[cite: 17]
    pulses = [9000, 4500]

    # 4. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(560)  # Mark is always ~560µs[cite: 17]
        pulses.append(1690 if bit == 1 else 560)  # Space: 1690µs for '1', 560µs for '0'[cite: 17]

    # Append the final stop bit mark to terminate the sequence
    pulses.append(560)

    return pulses