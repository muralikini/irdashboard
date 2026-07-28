# encoders/panasonic.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Panasonic 48-bit protocol fields into a Mark/Space timing array."""
    
    # 1. Parse fields or provide standard Panasonic defaults
    # Address can represent the system/device block, Command is 8-bit
    cmd = int(str(command_hex), 16) & 0xFF if command_hex else 0x00
    addr = int(str(address_hex), 16) if address_hex else 0x2002  # Default Panasonic Manufacturer Code example
    
    # Default Panasonic structure fields
    manufacturer = 0x0B02  # Common Panasonic ID prefix or customizable via address
    system = 0x20
    device = 0x00
    checksum = 0x00

    if addr > 0xFFFF:
        manufacturer = (addr >> 16) & 0xFFFF
        system = (addr >> 8) & 0xFF
        device = addr & 0xFF
    elif addr > 0xFF:
        system = (addr >> 8) & 0xFF
        device = addr & 0xFF
    else:
        system = addr & 0xFF

    # If payload is provided, use it for custom manufacturer/system overrides
    if payload_hex and str(payload_hex).strip():
        custom_pay = int(str(payload_hex), 16) & 0xFFFFFFFFFFFF
        manufacturer = (custom_pay >> 32) & 0xFFFF
        system = (custom_pay >> 24) & 0xFF
        device = (custom_pay >> 16) & 0xFF
        cmd = (custom_pay >> 8) & 0xFF

    # Calculate basic XOR checksum if not explicitly supplied (System ^ Device ^ Command)
    checksum = system ^ device ^ cmd

    # 2. Build the 6 bytes array
    byte_0 = (manufacturer >> 8) & 0xFF
    byte_1 = manufacturer & 0xFF
    byte_2 = system & 0xFF
    byte_3 = device & 0xFF
    byte_4 = cmd & 0xFF
    byte_5 = checksum & 0xFF

    bytes_arr = [byte_0, byte_1, byte_2, byte_3, byte_4, byte_5]
    
    bits = []

    def append_byte_lsb(val):
        """Appends 8 bits of a byte, LSB first."""
        for i in range(8):
            bit = (val >> i) & 1
            bits.append(bit)

    # 3. Assemble the 48-bit stream (LSB first per byte)
    for b in bytes_arr:
        append_byte_lsb(b)

    # 4. Panasonic Header: 3456µs mark, 1728µs space
    pulses = [3456, 1728]

    # 5. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(432)  # Mark is always ~432µs
        pulses.append(1296 if bit == 1 else 432)  # Space: 1296µs for '1', 432µs for '0'

    # Append the final stop bit mark to terminate the sequence
    pulses.append(432)

    return pulses