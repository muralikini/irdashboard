# encoders/encoder_registry.py
from encoders import nec, rc5, rc6, rca, sony, apple, bo, denon, jvc, kaseikyo, lg, nrc17, onkyo, panasonic, rcmm, samsung, sanyo, sharp, xmp, zenith

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
        
    elif proto_upper == "APPLE":
        return apple.encode(addr, cmd, pay)
        
    elif proto_upper in ["BO", "BANG & OLUFSEN"]:
        return bo.encode(addr, cmd, pay)
        
    elif proto_upper == "DENON":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        return denon.encode(addr, cmd)
        
    elif proto_upper == "JVC":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        return jvc.encode(addr, cmd)
        
    elif proto_upper in ["KASEIKYO", "KASEIKYO (GENERIC)"]:
        return kaseikyo.encode(addr, cmd, pay)
        
    elif proto_upper in ["LG", "LG 32-BIT", "LG 28-BIT"]:
        return lg.encode(addr, cmd, pay)
        
    elif proto_upper in ["NRC17", "NOKIA NRC17"]:
        return nrc17.encode(addr, cmd, pay)
        
    elif proto_upper == "ONKYO":
        addr = addr or "0x0000"
        cmd = cmd or "0x0000"
        return onkyo.encode(addr, cmd, pay)
        
    elif proto_upper == "PANASONIC":
        return panasonic.encode(addr, cmd, pay)
        
    elif proto_upper in ["RCMM", "RC-MM"]:
        return rcmm.encode(addr, cmd, pay)
        
    elif proto_upper in ["SAMSUNG", "SAMSUNG/RCA-32 VARIANT"]:
        return samsung.encode(addr, cmd, pay)
        
    elif proto_upper in ["SANYO", "SANYO (42-BIT)"]:
        return sanyo.encode(addr, cmd, pay)
        
    elif proto_upper == "SHARP":
        return sharp.encode(addr, cmd, pay)
        
    elif proto_upper == "XMP":
        return xmp.encode(addr, cmd, pay)
        
    elif proto_upper == "ZENITH":
        return zenith.encode(addr, cmd, pay)
        
    else:
        raise ValueError(f"Encoder for protocol '{proto_upper}' is not yet implemented.")