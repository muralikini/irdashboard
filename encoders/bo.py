# encoders/bo.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Bang & Olufsen (455 kHz) fields into a Mark/Space timing array."""
    
    # 1. Determine the 16-bit payload
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0xFFFF
    else:
        addr = int(str(address_hex), 16) & 0xFF if address_hex else 0
        cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0
        payload = (addr << 8) | cmd
        
    # 2. Extract bits (16 bits, MSB first)
    bits = [(payload >> i) & 1 for i in range(15, -1, -1)]
    
    pulses = []
    
    # 3. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(200)  # B&O Mark is always strictly 200µs
        pulses.append(6250 if bit == 1 else 3125)  # Space: 6250µs for '1', 3125µs for '0'
        
    # 4. Append final stop mark (Trailer) to close out the final space
    pulses.append(200)
    
    return pulses