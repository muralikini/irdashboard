# encoders/lg.py

def encode(address_hex, command_hex, payload_hex=""):
    """
    Encodes LG protocol fields into a Mark/Space timing array.
    Supports both 32-bit (NEC-like) and 28-bit variants.
    """
    
    # 1. Parse fields
    addr = int(str(address_hex), 16) if address_hex else 0x04
    cmd = int(str(command_hex), 16) if command_hex else 0x08
    
    # Check if a specific 28-bit checksum or custom length is requested via payload
    use_28_bit = False
    checksum = 0x0
    if payload_hex and str(payload_hex).strip():
        # If payload is provided, treat it as a 28-bit variant where payload holds the extra bits/checksum
        use_28_bit = True
        checksum = int(str(payload_hex), 16) & 0xF

    bits = []

    def append_byte_lsb(val):
        """Appends 8 bits of a value, LSB first."""
        for i in range(8):
            bit = (val >> i) & 1
            bits.append(bit)

    # 2. Construct Bit Stream Based on Variant
    if use_28_bit or (cmd > 0xFF):
        # --- LG 28-bit Mode: 8-bit Address, 16-bit Command, 4-bit Checksum ---
        addr = addr & 0xFF
        cmd = cmd & 0xFFFF
        
        # 8-bit Address (LSB first)
        append_byte_lsb(addr)
        
        # 16-bit Command (LSB first across two bytes)
        append_byte_lsb(cmd & 0xFF)
        append_byte_lsb((cmd >> 8) & 0xFF)
        
        # 4-bit Checksum (LSB first)
        for i in range(4):
            bits.append((checksum >> i) & 1)
            
    else:
        # --- LG 32-bit Mode: Address, Inv Address, Command, Inv Command ---
        addr = addr & 0xFF
        cmd = cmd & 0xFF
        
        addr_inv = (~addr) & 0xFF
        cmd_inv = (~cmd) & 0xFF
        
        append_byte_lsb(addr)
        append_byte_lsb(addr_inv)
        append_byte_lsb(cmd)
        append_byte_lsb(cmd_inv)

    # 3. LG Header: 9000µs mark, 4500µs space
    pulses = [9000, 4500]

    # 4. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(560)  # Mark is always ~560µs
        pulses.append(1680 if bit == 1 else 560)  # Space: 1680µs for '1', 560µs for '0'

    # Append the final stop bit mark
    pulses.append(560)

    return pulses