# encoders/sony.py

def encode(address_hex, command_hex, extended_hex=""):
    """
    Encodes Sony SIRC Hex Address, Command, and optional Extended data 
    into a precise single-frame Mark/Space timing array.
    """
    cmd = int(str(command_hex), 16) & 0x7F  # 7-bit command
    addr = int(str(address_hex), 16) if address_hex else 0
    
    # Safely handle None, NaN, or "None" strings from the data editor
    has_ext = False
    if extended_hex is not None:
        ext_str = str(extended_hex).strip().lower()
        if ext_str and ext_str != "none" and ext_str != "nan":
            has_ext = True

    bits = []
    # Command: 7 bits, LSB first
    bits.extend([(cmd >> i) & 1 for i in range(7)])
    
    # Address / Extended handling based on SIRC length (12, 15, or 20 bit)
    if has_ext:
        addr = addr & 0x1F  
        ext = int(str(extended_hex), 16) & 0xFF  
        bits.extend([(addr >> i) & 1 for i in range(5)])
        bits.extend([(ext >> i) & 1 for i in range(8)])
    elif addr > 0x1F:
        # 15-bit mode: 7-bit cmd + 8-bit addr
        addr = addr & 0xFF  
        bits.extend([(addr >> i) & 1 for i in range(8)])
    else:
        # 12-bit mode: 7-bit cmd + 5-bit addr
        addr = addr & 0x1F  
        bits.extend([(addr >> i) & 1 for i in range(5)])
        
    # Sony SIRC Protocol Timing Specifications:
    pulses = [2400, 600] # Header: 2400µs mark, 600µs space
    
    for i, bit in enumerate(bits):
        pulses.append(1200 if bit == 1 else 600)  # Mark
        pulses.append(600)                        # Space
            
    return pulses