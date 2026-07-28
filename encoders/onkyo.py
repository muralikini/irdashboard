# encoders/onkyo.py

def encode(address_hex, command_hex, payload_hex=""):
    """Encodes Onkyo 32-bit protocol fields into a Mark/Space timing array."""
    
    # 1. Parse fields (16-bit Address and 16-bit Command)
    addr = int(str(address_hex), 16) & 0xFFFF if address_hex else 0x0000
    cmd = int(str(command_hex), 16) & 0xFFFF if command_hex else 0x0000

    # 2. Split into 4 distinct bytes for the 32-bit payload structure
    byte_0 = (addr >> 8) & 0xFF
    byte_1 = addr & 0xFF
    byte_2 = (cmd >> 8) & 0xFF
    byte_3 = cmd & 0xFF

    bytes_arr = [byte_0, byte_1, byte_2, byte_3]
    
    bits = []

    def append_byte_lsb(val):
        """Appends 8 bits of a byte, LSB first."""
        for i in range(8):
            bit = (val >> i) & 1
            bits.append(bit)

    # 3. Assemble the 32-bit stream (LSB first per byte)
    for b in bytes_arr:
        append_byte_lsb(b)

    # 4. Onkyo Header: 9000µs mark, 4500µs space
    pulses = [9000, 4500]

    # 5. Convert logical bits to Microsecond Pulses
    for bit in bits:
        pulses.append(560)  # Mark is always ~560µs[cite: 16]
        pulses.append(1690 if bit == 1 else 560)  # Space: 1690µs for '1', 560µs for '0'[cite: 16]

    # Append the final stop bit mark to terminate the sequence
    pulses.append(560)

    return pulses