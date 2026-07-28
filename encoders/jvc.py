# encoders/jvc.py

def encode(address_hex, command_hex):
    """Encodes JVC Hex Address and Command into a Mark/Space timing array."""
    
    # 1. Parse hex to integers, enforcing 8-bit constraints (0-255)
    addr = int(str(address_hex), 16) & 0xFF
    cmd = int(str(command_hex), 16) & 0xFF
    
    # 2. Assemble the 16 logical bits (LSB first for both fields)
    bits = []
    
    # Address: 8 bits, LSB first
    bits.extend([(addr >> i) & 1 for i in range(8)])
    
    # Command: 8 bits, LSB first
    bits.extend([(cmd >> i) & 1 for i in range(8)])
    
    # 3. Convert logical bits to Microsecond Pulses
    # JVC Header: 8416µs mark, 4208µs space
    pulses = [8416, 4208]
    
    for bit in bits:
        pulses.append(526)  # Mark is always ~526µs
        pulses.append(1578 if bit == 1 else 526)  # Space: 1578µs for '1', 526µs for '0'
        
    # Append the final stop bit mark to terminate the last space
    pulses.append(526)
    
    return pulses