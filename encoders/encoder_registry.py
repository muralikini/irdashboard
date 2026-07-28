# encoders/encoder_registry.py
from encoders import nec

def generate_pulses(protocol, address, command, payload):
    """
    Routes the encoding request to the correct protocol module
    and returns the Mark/Space microsecond array.
    """
    proto_upper = str(protocol).strip().upper()
    
    if proto_upper == "NEC":
        # Ensure address and command default to '0x00' if left empty
        addr = address.strip() if address else "0x00"
        cmd = command.strip() if command else "0x00"
        return nec.encode(addr, cmd)
        
    # Future protocols (RC5, SONY, etc.) will go here as elif statements
    else:
        raise ValueError(f"Encoder for protocol '{proto_upper}' is not yet implemented.")