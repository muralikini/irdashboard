# encoders/sharp.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Sharp protocol fields into a Mark/Space timing array."""
    
    # 1. Parse fields (5-bit Address and 8-bit Command)
    addr = int(str(address_hex), 16) & 0x1F if address_hex else 0x00
    cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0x00
    
    # Expansion and Check bits (Check bit is the logical inverse of EXP)
    exp_bit = 0
    chk_bit = 1
    
    if payload_hex and str(payload_hex).strip():
        pay = int(str(payload_hex), 16)
        exp_bit = (pay >> 1) & 1
        chk_bit = ~exp_bit & 1

    # 2. Assemble the 15 logical bits (LSB first for data fields)
    bits = []
    
    # Address: 5 bits, LSB first[cite: 18]
    bits.extend([(addr >> i) & 1 for i in range(5)])
    
    # Command: 8 bits, LSB first[cite: 18]
    bits.extend([(cmd >> i) & 1 for i in range(8)])
    
    # EXP and CHK bits
    bits.append(exp_bit)
    bits.append(chk_bit)

    # 3. Convert logical bits to Microsecond Pulses
    pulses = []
    
    # Note: Sharp does not use a header pulse. It starts directly with data.[cite: 18]
    for bit in bits:
        pulses.append(320)  # Mark is always ~320µs[cite: 18]
        pulses.append(1680 if bit == 1 else 680)  # Space: 1680µs for '1', 680µs for '0'[cite: 18]
        
    # Append the final stop bit mark to terminate the last space
    pulses.append(320)

    return pulses