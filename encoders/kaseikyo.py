# encoders/kaseikyo.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Kaseikyo 48-bit protocol fields into a Mark/Space timing array."""
    
    # 1. Determine the 48-bit payload (12 hex characters / 6 bytes)
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16) & 0xFFFFFFFFFFFF
    else:
        # Fallback if specific payload is blank: build a dummy 48-bit value from addr/cmd
        addr = int(str(address_hex), 16) & 0xFFFF if address_hex else 0x3200
        cmd = int(str(command_hex), 16) & 0xFFFF if command_hex else 0x00
        payload = (addr << 32) | (cmd << 16)
        
    # 2. Extract bits (48 bits, LSB first since the decoder reverses them back)
    bits = [(payload >> i) & 1 for i in range(48)]
    
    # 3. Kaseikyo Header: 3456µs mark, 1728µs space
    pulses = [3456, 1728]
    
    # 4. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(432)  # Mark is always ~432µs
        pulses.append(1296 if bit == 1 else 432)  # Space: 1296µs for '1', 432µs for '0'
        
    # Append the final stop bit mark to terminate the last space
    pulses.append(432)
    
    return pulses