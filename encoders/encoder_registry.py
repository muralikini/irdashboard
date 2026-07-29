# encoders/encoder_registry.py
from encoders.protocol_generator import generate_protocol_pulses

def generate_pulses(protocol, address, command, payload=""):
    """
    Universal dispatcher that generates pulses using the master protocol database.
    """
    return generate_protocol_pulses(protocol, address, command, payload)