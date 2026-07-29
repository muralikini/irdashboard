# encoders/protocol_generator.py
import os
import json

def load_protocols():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    json_path = os.path.join(root_dir, "protocols_master.json")
    if not os.path.exists(json_path):
        json_path = "protocols_master.json"
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def generate_protocol_pulses(protocol_name, address_hex, command_hex, payload=""):
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
    encoding_type = proto.get("encoding_type", "ppm")
    struct = proto.get("transmission_structure", {})
    target_frame_count = struct.get("frame_count", 1)
    separator_gap = struct.get("separator_gap_us", 40000)

    single_frame_pulses = []

    # --- RC5 MANCHESTER GENERATION ---
    if encoding_type == "manchester":
        T = proto.get("unit_us", 889)
        s1 = 1
        s2 = 1 if cmd < 64 else 0
        if cmd >= 64:
            cmd = cmd & 0x3F
            
        toggle = 0
        addr = addr & 0x1F
        
        bits = [s1, s2, toggle]
        bits.extend([(addr >> i) & 1 for i in range(4, -1, -1)])
        bits.extend([(cmd >> i) & 1 for i in range(5, -1, -1)])
        
        half_bits = []
        for bit in bits:
            if bit == 1:
                half_bits.extend([0, 1])
            else:
                half_bits.extend([1, 0])
                
        half_bits = half_bits[1:]
        
        current_level = 1
        duration = 0
        for hb in half_bits:
            if hb == current_level:
                duration += T
            else:
                single_frame_pulses.append(duration)
                current_level = hb
                duration = T
        single_frame_pulses.append(duration)

    # --- STANDARD PPM GENERATION ---
    else:
        layout = proto.get("byte_layout", ["addr", "cmd"])
        bytes_arr = []
        for item in layout:
            if item == "addr": bytes_arr.append(addr & 0xFF)
            elif item == "addr_inv": bytes_arr.append((~addr) & 0xFF)
            elif item == "cmd": bytes_arr.append(cmd & 0xFF)
            elif item == "cmd_inv": bytes_arr.append((~cmd) & 0xFF)

        bits = []
        bit_order = proto.get("bit_order", "lsb")
        for b in bytes_arr:
            for i in range(8):
                bits.append((b >> i) & 1 if bit_order == "lsb" else (b >> (7 - i)) & 1)

        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 9000), hdr.get("space_us", 4500)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})

        for bit in bits:
            if bit == 1:
                single_frame_pulses.extend([l1.get("mark_us", 565), l1.get("space_us", 1690)])
            else:
                single_frame_pulses.extend([l0.get("mark_us", 565), l0.get("space_us", 565)])

        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0:
            single_frame_pulses.append(stop.get("mark_us", 565))
            if stop.get("space_us", 0) > 0:
                single_frame_pulses.append(stop.get("space_us", 565))

    # --- ASSEMBLE MULTI-FRAME SEQUENCE (Looping Frame Count) ---
    complete_pulses = []
    for f_idx in range(target_frame_count):
        if f_idx > 0 and separator_gap > 0:
            complete_pulses.append(separator_gap)
        complete_pulses.extend(single_frame_pulses)

    # Append standard repeat frame if configured
    if struct.get("has_repeat_frame", False):
        if separator_gap > 0:
            complete_pulses.append(separator_gap)
        rep = struct.get("repeat_frame", {})
        complete_pulses.extend([
            rep.get("mark_us", 9000),
            rep.get("space_us", 2250),
            rep.get("stop_us", 565)
        ])

    return complete_pulses