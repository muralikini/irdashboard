# encoders/nec.py

def encode(address_hex, command_hex):
    """Encodes NEC Hex Address and Command into a Mark/Space timing array."""
    # Convert hex strings to integers
    address = int(str(address_hex), 16)
    command = int(str(command_hex), 16)
    
    # Calculate logical inverses (standard NEC requires this for error checking)
    addr_inv = (~address) & 0xFF
    cmd_inv = (~command) & 0xFF
    
    # Start with the standard NEC Header (9000us mark, 4500us space)
    pulses = [9000, 4500]
    
    def append_byte(val):
        """Appends 8 bits of a byte to the pulse array, LSB first."""
        for i in range(8):
            bit = (val >> i) & 1
            pulses.append(560) # Mark is always ~560us
            pulses.append(1690 if bit else 560) # Space is 1690us for '1', 560us for '0'
            
    # Assemble the 32-bit payload
    append_byte(address)
    append_byte(addr_inv)
    append_byte(command)
    append_byte(cmd_inv)
    
    # Append final stop bit mark to terminate the sequence
    pulses.append(560)
    
    return pulses