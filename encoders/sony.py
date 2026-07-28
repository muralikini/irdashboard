# encoders/sony.py

def encode(address_hex, command_hex, extended_hex=""):
    """
    Encodes Sony SIRC Hex Address, Command, and optional Extended data 
    into a Mark/Space timing array. Auto-detects 12, 15, or 20-bit modes.
    """
    
    # 1. Parse hex to integers
    cmd = int(str(command_hex), 16) & 0x7F  # Command is always 7 bits max
    addr = int(str(address_hex), 16) if address_hex else 0
    
    bits = []
    
    # 2. Command (7 bits, LSB first)
    bits.extend([(cmd >> i) & 1 for i in range(7)])
    
    # 3. Determine Mode and Append Data
    if extended_hex and str(extended_hex).strip():
        # 20-bit mode: 7-bit command + 5-bit address + 8-bit extended
        addr = addr & 0x1F  
        ext = int(str(extended_hex), 16) & 0xFF  
        bits.extend([(addr >> i) & 1 for i in range(5)])
        bits.extend([(ext >> i) & 1 for i in range(8)])
        
    elif addr > 0x1F:
        # 15-bit mode: 7-bit command + 8-bit address (Triggered if Address > 31)
        addr = addr & 0xFF  
        bits.extend([(addr >> i) & 1 for i in range(8)])
        
    else:
        # 12-bit mode (Standard): 7-bit command + 5-bit address
        addr = addr & 0x1F  
        bits.extend([(addr >> i) & 1 for i in range(5)])
        
    # 4. Convert logical bits to Microsecond Pulses
    # Sony Header: 2400µs mark, 600µs space
    pulses = [2400, 600]
    
    for i, bit in enumerate(bits):
        # Mark: 1200µs for '1', 600µs for '0'
        pulses.append(1200 if bit == 1 else 600)  
        
        # Space: strictly 600µs (Do not append a space after the final mark)
        if i < len(bits) - 1:
            pulses.append(600)
            
    return pulses