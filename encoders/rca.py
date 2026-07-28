# encoders/rca.py

def encode(address_hex, command_hex):
    """Encodes RCA Hex Address and Command into a Mark/Space timing array."""
    
    # 1. Parse hex to integers, enforcing bit constraints
    # Address is 4 bits (0-15), Command is 8 bits (0-255)
    addr = int(str(address_hex), 16) & 0xF
    cmd = int(str(command_hex), 16) & 0xFF
    
    # 2. Calculate logical inverses for the checksum
    inv_addr = (~addr) & 0xF
    inv_cmd = (~cmd) & 0xFF
    
    # 3. Assemble the 24 logical bits
    bits = []
    
    # Address: 4 bits, MSB first
    bits.extend([(addr >> i) & 1 for i in range(3, -1, -1)])
    
    # Command: 8 bits, LSB first
    bits.extend([(cmd >> i) & 1 for i in range(8)])
    
    # Inverted Address: 4 bits, MSB first
    bits.extend([(inv_addr >> i) & 1 for i in range(3, -1, -1)])
    
    # Inverted Command: 8 bits, LSB first
    bits.extend([(inv_cmd >> i) & 1 for i in range(8)])
    
    # 4. Convert logical bits to Microsecond Pulses
    # RCA Header: 4000µs mark, 4000µs space
    pulses = [4000, 4000]
    
    for bit in bits:
        pulses.append(500)  # Mark is always ~500µs
        pulses.append(2000 if bit == 1 else 1000)  # Space: 2000µs for '1', 1000µs for '0'
        
    # Append the final stop bit mark to terminate the last space
    pulses.append(500)
    
    return pulses