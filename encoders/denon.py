# encoders/denon.py

def encode(address_hex, command_hex):
    """Encodes Denon Hex Address and Command into a Mark/Space timing array."""
    
    # 1. Parse hex to integers, enforcing bit constraints
    # Address is 5 bits (0-31), Command is 10 bits (0-1023)
    addr = int(str(address_hex), 16) & 0x1F
    cmd = int(str(command_hex), 16) & 0x3FF
    
    # 2. Assemble the 15 logical bits (LSB first for both fields)
    bits = []
    
    # Address: 5 bits, LSB first
    bits.extend([(addr >> i) & 1 for i in range(5)])
    
    # Command: 10 bits, LSB first
    bits.extend([(cmd >> i) & 1 for i in range(10)])
    
    # 3. Convert logical bits to Microsecond Pulses
    pulses = []
    
    # Note: Denon does not use a header pulse. It starts directly with the data.
    for bit in bits:
        pulses.append(275)  # Mark is always ~275µs
        pulses.append(1900 if bit == 1 else 775)  # Space: 1900µs for '1', 775µs for '0'
        
    # Append the final stop bit mark to terminate the last space
    pulses.append(275)
    
    return pulses