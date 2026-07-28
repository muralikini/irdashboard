# encoders/samsung.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Samsung/RCA-32 variant protocol fields into a Mark/Space timing array."""
    
    # 1. Determine the 32-bit payload value
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0xFFFFFFFF
    else:
        addr = int(str(address_hex), 16) & 0xFFFF if address_hex else 0x0707
        cmd = int(str(command_hex), 16) & 0xFFFF if command_hex else 0x0202
        payload = (addr << 16) | cmd

    # 2. Extract bits (32 bits, LSB first since the decoder reverses them)
    bits = [(payload >> i) & 1 for i in range(32)]

    # 3. Samsung Header: 4500µs mark, 4500µs space[cite: 17]
    pulses = [4500, 4500]

    # 4. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(560)  # Mark is always ~560µs[cite: 17]
        pulses.append(1690 if bit == 1 else 560)  # Space: 1690µs for '1', 560µs for '0'[cite: 17]

    # Append the final stop bit mark to terminate the sequence
    pulses.append(560)

    return pulses