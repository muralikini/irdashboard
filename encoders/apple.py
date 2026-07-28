# encoders/encoder_registry.py
from encoders import nec, rc5, rc6, rca, sony

def generate_pulses(protocol, address, command, payload):
    """
    Routes the encoding request to the correct protocol module
    and returns the Mark/Space microsecond array.
    """
    proto_upper = str(protocol).strip().upper()
    
    # Extract values, handling empty cells gracefully
    addr = str(address).strip() if address else ""
    cmd = str(command).strip() if command else ""
    pay = str(payload).strip() if payload else ""
    
    if proto_upper == "NEC":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        return nec.encode(addr, cmd)
        
    elif proto_upper == "RC5":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        return rc5.encode(addr, cmd)
        
    elif proto_upper == "RC6":
        return rc6.encode(addr, cmd, pay)
        
    elif proto_upper == "RCA":
        addr = addr or "0x0"
        cmd = cmd or "0x00"
        return rca.encode(addr, cmd)
        
    elif proto_upper == "SONY":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        return sony.encode(addr, cmd, pay)
        
    else:
        raise ValueError(f"Encoder for protocol '{proto_upper}' is not yet implemented.")