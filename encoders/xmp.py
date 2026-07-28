# encoders/xmp.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes XMP protocol fields into a Mark/Space timing array using nibble spacing."""
    
    # 1. Determine the payload hex string
    if payload_hex and str(payload_hex).strip():
        hex_str = str(payload_hex).strip().replace("0x", "")
    else:
        addr = str(address_hex).strip().replace("0x", "") if address_hex else "00"
        cmd = str(command_hex).strip().replace("0x", "") if command_hex else "00"
        hex_str = addr + cmd

    # 2. Convert the hex string into an array of 4-bit nibbles
    nibbles = []
    for char in hex_str:
        nibbles.append(int(char, 16))

    if not nibbles:
        nibbles = [0, 0, 0, 0]

    # 3. Convert nibbles to Microsecond Pulses
    pulses = []
    
    for nibble in nibbles:
        # XMP mark is consistently ~210µs[cite: 18]
        pulses.append(210)
        
        # Space formula: 760µs + (nibble * 138µs)[cite: 18]
        target_space = 760 + (nibble * 138)
        pulses.append(target_space)

    # Append a final trailing burst to close the sequence
    pulses.append(210)

    return pulses