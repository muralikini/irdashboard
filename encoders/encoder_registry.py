# encoders/encoder_registry.py
from encoders.protocol_generator import generate_protocol_pulses

def generate_pulses(protocol, address, command, payload=""):
    """
    Universal dispatcher routing generation requests through the master protocol database.
    """
    proto_upper = str(protocol).strip().upper()
    
    # Handle Apple default address if left blank
    if proto_upper == "APPLE" and (not address or not str(address).strip()):
        address = "0x87EE"
        
    return generate_protocol_pulses(proto_upper, address, command, payload)