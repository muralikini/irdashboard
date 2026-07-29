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

def generate_protocol_pulses(protocol_name, address_hex, command_hex, payload_hex=""):
    protocols = load_protocols()
    proto = protocols.get(protocol_name.upper())
    
    if not proto:
        raise ValueError(f"Protocol '{protocol_name}' not found in master database.")

    def parse_hex(val, default=0):
        if val is None: return default
        v_str = str(val).strip().lower()
        if not v_str or v_str == "none" or v_str == "nan": return default
        return int(v_str, 16)

    proto_upper = protocol_name.upper()
    
    # Apple defaults to 0x87EE address if not explicitly specified
    if proto_upper == "APPLE":
        addr = parse_hex(address_hex, 0x87EE)
    else:
        addr = parse_hex(address_hex, 0)
        
    cmd = parse_hex(command_hex, 0)
    encoding_type = proto.get("encoding_type", "ppm")
    struct = proto.get("transmission_structure", {})
    target_frame_count = struct.get("frame_count", 1)
    separator_gap = struct.get("separator_gap_us", 40000)

    single_frame_pulses = []

    # --- SONY GENERATION PATH ---
    if encoding_type == "sony":
        c_val = cmd & 0x7F
        a_val = addr
        bits = []
        bits.extend([(c_val >> i) & 1 for i in range(7)])
        
        if payload_hex and str(payload_hex).strip():
            a_val = a_val & 0x1F
            ext = parse_hex(payload_hex, 0) & 0xFF
            bits.extend([(a_val >> i) & 1 for i in range(5)])
            bits.extend([(ext >> i) & 1 for i in range(8)])
        elif a_val > 0x1F:
            a_val = a_val & 0xFF
            bits.extend([(a_val >> i) & 1 for i in range(8)])
        else:
            a_val = a_val & 0x1F
            bits.extend([(a_val >> i) & 1 for i in range(5)])
            
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 2400), hdr.get("space_us", 600)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        
        for i, bit in enumerate(bits):
            single_frame_pulses.append(l1.get("mark_us", 1200) if bit == 1 else l0.get("mark_us", 600))
            if i < len(bits) - 1:
                single_frame_pulses.append(l0.get("space_us", 600))

    # --- NRC17 GENERATION PATH ---
    elif encoding_type == "nrc17":
        T = proto.get("unit_us", 500)
        c_val = cmd & 0xFF
        a_val = addr & 0xF
        sub_val = parse_hex(payload_hex, 0x0) & 0xF

        logical_bits = [1] + [(c_val >> i) & 1 for i in range(8)] + [(a_val >> i) & 1 for i in range(4)] + [(sub_val >> i) & 1 for i in range(4)]
        half_bits = []
        for bit in logical_bits:
            half_bits.extend([1, 0] if bit == 1 else [0, 1])

        single_frame_pulses = [1 * T, 5 * T]
        current_level, duration = 1, 0
        for hb in half_bits:
            if hb == current_level: duration += T
            else:
                single_frame_pulses.append(duration)
                current_level, duration = hb, T
        single_frame_pulses.append(duration)

    # --- RCA GENERATION PATH ---
    elif encoding_type == "rca":
        addr_4 = addr & 0xF
        cmd_8 = cmd & 0xFF
        inv_addr, inv_cmd = (~addr_4) & 0xF, (~cmd_8) & 0xFF
        
        bits = []
        bits.extend([(addr_4 >> i) & 1 for i in range(3, -1, -1)])
        bits.extend([(cmd_8 >> i) & 1 for i in range(8)])
        bits.extend([(inv_addr >> i) & 1 for i in range(3, -1, -1)])
        bits.extend([(inv_cmd >> i) & 1 for i in range(8)])
        
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 4000), hdr.get("space_us", 4000)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 500), l1.get("space_us", 2000)] if bit == 1 else [l0.get("mark_us", 500), l0.get("space_us", 1000)])
        if proto.get("stop_bit", {}).get("mark_us", 0) > 0:
            single_frame_pulses.append(500)

    # --- RC6 MODE 0 GENERATION ---
    elif encoding_type == "rc6":
        T = proto.get("unit_us", 444)
        p_val = parse_hex(payload_hex, -1)
        payload = p_val & 0xFFFF if p_val >= 0 else ((addr & 0xFF) << 8) | (cmd & 0xFF)
        
        logical_bits = [1, 0, 0, 0, 0] + [(payload >> i) & 1 for i in range(15, -1, -1)]
        t_units = [1, 1, 1, 1, 1, 1, 0, 0]
        
        for i, bit in enumerate(logical_bits):
            if i == 4:
                t_units.extend([1, 1, 0, 0] if bit == 1 else [0, 0, 1, 1])
            else:
                t_units.extend([1, 0] if bit == 1 else [0, 1])
                
        current_level, duration = 1, 0
        for tu in t_units:
            if tu == current_level: duration += T
            else:
                single_frame_pulses.append(duration)
                current_level, duration = tu, T
        single_frame_pulses.append(duration)

    # --- RC5 MANCHESTER GENERATION ---
    elif encoding_type == "manchester":
        T = proto.get("unit_us", 889)
        s2 = 1 if cmd < 64 else 0
        if cmd >= 64: cmd = cmd & 0x3F
        
        bits = [1, s2, 0] + [(addr >> i) & 1 for i in range(4, -1, -1)] + [(cmd >> i) & 1 for i in range(5, -1, -1)]
        half_bits = []
        for bit in bits:
            half_bits.extend([0, 1] if bit == 1 else [1, 0])
        half_bits = half_bits[1:]
        
        current_level, duration = 1, 0
        for hb in half_bits:
            if hb == current_level: duration += T
            else:
                single_frame_pulses.append(duration)
                current_level, duration = hb, T
        single_frame_pulses.append(duration)

    # --- STANDARD PPM / APPLE GENERATION ---
    else:
        layout = proto.get("byte_layout", ["addr", "addr_inv", "cmd", "cmd_inv"])
        bytes_arr = []
        for item in layout:
            if item == "addr":
                bytes_arr.append(addr & 0xFF)
            elif item == "addr_inv":
                bytes_arr.append((~addr) & 0xFF)
            elif item == "addr_low":
                bytes_arr.append(addr & 0xFF)
            elif item == "addr_high":
                bytes_arr.append((addr >> 8) & 0xFF)
            elif item == "addr_high_inv":
                bytes_arr.append((~(addr >> 8)) & 0xFF)
            elif item == "cmd":
                bytes_arr.append(cmd & 0xFF)
            elif item == "cmd_inv":
                bytes_arr.append((~cmd) & 0xFF)

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

    # --- ASSEMBLE MULTI-FRAME SEQUENCE ---
    complete_pulses = []
    for f_idx in range(target_frame_count):
        if f_idx > 0 and separator_gap > 0:
            complete_pulses.append(separator_gap)
        complete_pulses.extend(single_frame_pulses)

    if struct.get("has_repeat_frame", False):
        if separator_gap > 0:
            complete_pulses.append(separator_gap)
        rep = struct.get("repeat_frame", {})
        complete_pulses.extend([rep.get("mark_us", 9000), rep.get("space_us", 2250), rep.get("stop_us", 565)])

    return complete_pulses