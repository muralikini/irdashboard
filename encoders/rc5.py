# encoders/rc5.py

def encode(address_hex, command_hex):
    """
    Encodes RC5 signals safely handling missing address/command or raw payloads.
    """
    # Safe parser helper for hex inputs
    def parse_hex_val(val, default=0):
        if val is None:
            return default
        val_str = str(val).strip().lower()
        if not val_str or val_str == "none" or val_str == "nan":
            return default
        return int(val_str, 16)
    
    addr = parse_hex_val(address_hex, 0)
    cmd = parse_hex_val(command_hex, 0)
    
    # 1. Extended RC5 Handling
    # If command is 64 or greater, S2 becomes 0 and we mask the command
    s1 = 1
    s2 = 1
    if cmd >= 64:
        s2 = 0
        cmd = cmd & 0x3F
        
    toggle = 0  # Default toggle bit for generated signals
    addr = addr & 0x1F  # Ensure Address is strictly 5 bits
    
    # 2. Construct the 14 logical bits (MSB first)
    bits = [s1, s2, toggle]
    bits.extend([(addr >> i) & 1 for i in range(4, -1, -1)])
    bits.extend([(cmd >> i) & 1 for i in range(5, -1, -1)])
    
    # 3. Manchester Encoding
    # Logical 1 = Space (0) then Mark (1)
    # Logical 0 = Mark (1) then Space (0)
    half_bits = []
    for bit in bits:
        if bit == 1:
            half_bits.extend([0, 1])
        else:
            half_bits.extend([1, 0])
            
    # IR transmitters do not send the leading Space; they start on the first Mark.
    half_bits = half_bits[1:]
    
    # 4. Convert half-bits to Microsecond Pulses
    T = 889  # Base RC5 half-bit duration in microseconds
    pulses = []
    current_level = 1
    duration = 0
    
    for hb in half_bits:
        if hb == current_level:
            duration += T
        else:
            pulses.append(duration)
            current_level = hb
            duration = T
            
    # Append the final sequence duration
    pulses.append(duration)
    
    return pulses