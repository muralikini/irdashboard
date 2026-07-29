# encoders/protocol_generator.py
import os
import json

def load_protocols():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(os.path.dirname(base_dir), "protocols_master.json")
    if not os.path.exists(json_path):
        json_path = "protocols_master.json"
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def generate_protocol_pulses(protocol_name, address_hex, command_hex, payload=""):
    """
    Generates a complete multi-frame timing pulse array dynamically 
    based on the master protocol database definition.
    """
    protocols = load_protocols()
    proto = protocols.get(protocol_name.upper())
    
    if not proto:
        raise ValueError(f"Protocol '{protocol_name}' not found in master database.")

    def parse_hex(val, default=0):
        if val is None: return default
        v_str = str(val).strip().lower()
        if not v_str or v_str == "none" or v_str == "nan": return default
        return int(v_str, 16)

    addr = parse_hex(address_hex, 0)
    cmd = parse_hex(command_hex, 0)

    # Build byte array layout based on protocol specification
    layout = proto.get("byte_layout", ["addr", "cmd"])
    bytes_arr = []
    
    for item in layout:
        if item == "addr":
            bytes_arr.append(addr & 0xFF)
        elif item == "addr_inv":
            bytes_arr.append((~addr) & 0xFF)
        elif item == "cmd":
            bytes_arr.append(cmd & 0xFF)
        elif item == "cmd_inv":
            bytes_arr.append((~cmd) & 0xFF)
        elif item == "addr_high":
            bytes_arr.append((addr >> 8) & 0xFF)
        elif item == "addr_high_inv":
            bytes_arr.append((~ (addr >> 8)) & 0xFF)
        elif item == "addr_low":
            bytes_arr.append(addr & 0xFF)

    # Convert bytes to bits (LSB or MSB first)
    bits = []
    bit_order = proto.get("bit_order", "lsb")
    for b in bytes_arr:
        for i in range(8):
            if bit_order == "lsb":
                bits.append((b >> i) & 1)
            else:
                bits.append((b >> (7 - i)) & 1)

    # Build Primary Frame
    hdr = proto.get("header", {})
    primary_frame = [hdr.get("mark_us", 9000), hdr.get("space_us", 4500)]

    l0 = proto.get("logical_0", {})
    l1 = proto.get("logical_1", {})

    for bit in bits:
        if bit == 1:
            primary_frame.append(l1.get("mark_us", 565))
            primary_frame.append(l1.get("space_us", 1690))
        else:
            primary_frame.append(l0.get("mark_us", 565))
            primary_frame.append(l0.get("space_us", 565))

    stop = proto.get("stop_bit", {})
    if stop.get("mark_us", 0) > 0:
        primary_frame.append(stop.get("mark_us", 565))
        if stop.get("space_us", 0) > 0:
            primary_frame.append(stop.get("space_us", 0))

    # Assemble Multi-Frame Sequence Train with Separator and Repeat Frame
    complete_pulses = []
    complete_pulses.extend(primary_frame)

    struct = proto.get("transmission_structure", {})
    if struct.get("has_repeat_frame", False):
        separator_gap = struct.get("separator_gap_us", 40000)
        complete_pulses.append(separator_gap)  # Inserted as a space duration

        rep = struct.get("repeat_frame", {})
        complete_pulses.extend([
            rep.get("mark_us", 9000),
            rep.get("space_us", 2250),
            rep.get("stop_us", 565)
        ])

    return complete_pulses