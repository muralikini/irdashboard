# encoders/rc6.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes RC6 protocol fields into a Mark/Space timing array."""
    
    # 1. Determine the 16-bit payload
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0xFFFF
    else:
        addr = int(str(address_hex), 16) & 0xFF if address_hex else 0
        cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0
        payload = (addr << 8) | cmd
        
    # 2. Define RC6 Mode 0 logical bits
    start_bit = 1
    mode_bits = [0, 0, 0]
    toggle_bit = 0  # Default to 0 for generated signals
    
    # Extract payload bits (MSB first)
    payload_bits = [(payload >> i) & 1 for i in range(15, -1, -1)]
    
    # Combine all logical bits into a single array
    logical_bits = [start_bit] + mode_bits + [toggle_bit] + payload_bits
    
    # 3. Convert to physical T-units (1 = Mark, 0 = Space)
    # The RC6 Header is a 6T Mark followed by a 2T Space
    t_units = [1, 1, 1, 1, 1, 1, 0, 0]
    
    for i, bit in enumerate(logical_bits):
        # Bit index 4 is the Toggle bit, which is twice as long (2T per half)
        if i == 4:
            if bit == 1:
                t_units.extend([1, 1, 0, 0])
            else:
                t_units.extend([0, 0, 1, 1])
        else:
            # Standard Manchester: 1 -> Mark/Space, 0 -> Space/Mark
            if bit == 1:
                t_units.extend([1, 0])
            else:
                t_units.extend([0, 1])
                
    # 4. Convert T-units to Microsecond Pulses
    T = 444  # Base RC6 half-bit duration in microseconds
    pulses = []
    current_level = 1
    duration = 0
    
    for tu in t_units:
        if tu == current_level:
            duration += T
        else:
            pulses.append(duration)
            current_level = tu
            duration = T
            
    # Append the final sequence duration
    pulses.append(duration)
    
    return pulses