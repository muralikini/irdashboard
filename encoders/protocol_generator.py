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

    # --- SAMSUNG GENERATION PATH ---
    if encoding_type == "samsung":
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0) & 0xFFFFFFFF
        else:
            a_val = parse_hex(address_hex, 0x0707) & 0xFFFF
            c_val = parse_hex(command_hex, 0x0202) & 0xFFFF
            payload = (a_val << 16) | c_val
            
        bits = [(payload >> i) & 1 for i in range(32)]
        hdr = proto.get("header", {})
        l0 = proto.get("logical_0", {})
        l1 = proto.get("logical_1", {})
        
        single_frame_pulses = [hdr.get("mark_us", 4500), hdr.get("space_us", 4500)]
        for bit in bits:
            if bit == 1:
                single_frame_pulses.extend([l1.get("mark_us", 560), l1.get("space_us", 1690)])
            else:
                single_frame_pulses.extend([l0.get("mark_us", 560), l0.get("space_us", 560)])
                
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0:
            single_frame_pulses.append(stop.get("mark_us", 560))
            
    # --- BANG & OLUFSEN (BO) GENERATION PATH ---
    elif encoding_type == "bo":
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0) & 0xFFFF
        else:
            a_val = addr & 0xFF
            c_val = cmd & 0xFF
            payload = (a_val << 8) | c_val
        bits = [(payload >> i) & 1 for i in range(15, -1, -1)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        single_frame_pulses = []
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 200), l1.get("space_us", 6250)] if bit == 1 else [l0.get("mark_us", 200), l0.get("space_us", 3125)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 200))

    # --- ZENITH GENERATION PATH ---
    elif encoding_type == "zenith":
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0) & 0x3FFFFF
        else:
            a_val = addr & 0xFF
            c_val = cmd & 0x3FFF
            payload = (a_val << 14) | c_val
        bits = [(payload >> i) & 1 for i in range(21, -1, -1)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        single_frame_pulses = []
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 520), l1.get("space_us", 1040)] if bit == 1 else [l0.get("mark_us", 520), l0.get("space_us", 520)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 520))

    # --- XMP GENERATION PATH ---
    elif encoding_type == "xmp":
        if payload_hex and str(payload_hex).strip():
            hex_str = str(payload_hex).strip().replace("0x", "")
        else:
            a_str = str(address_hex).strip().replace("0x", "") if address_hex else "00"
            c_str = str(command_hex).strip().replace("0x", "") if command_hex else "00"
            hex_str = a_str + c_str
        nibbles = [int(char, 16) for char in hex_str]
        if not nibbles: nibbles = [0, 0, 0, 0]
        single_frame_pulses = []
        for nibble in nibbles:
            single_frame_pulses.append(210)
            single_frame_pulses.append(760 + (nibble * 138))
        single_frame_pulses.append(210)

    # --- SHARP GENERATION PATH ---
    elif encoding_type == "sharp":
        a_val = parse_hex(address_hex, 0x00) & 0x1F
        c_val = parse_hex(command_hex, 0x00) & 0xFF
        exp_bit, chk_bit = 0, 1
        if payload_hex and str(payload_hex).strip():
            pay = parse_hex(payload_hex, 0)
            exp_bit = (pay >> 1) & 1
            chk_bit = ~exp_bit & 1
        bits = []
        bits.extend([(a_val >> i) & 1 for i in range(5)])
        bits.extend([(c_val >> i) & 1 for i in range(8)])
        bits.append(exp_bit)
        bits.append(chk_bit)
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        single_frame_pulses = []
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 320), l1.get("space_us", 1680)] if bit == 1 else [l0.get("mark_us", 320), l0.get("space_us", 680)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 320))

    # --- SANYO GENERATION PATH ---
    elif encoding_type == "sanyo":
        a_val = parse_hex(address_hex, 0x1F00) & 0x1FFF
        c_val = parse_hex(command_hex, 0x50) & 0xFF
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0) & 0x3FFFFFFFFFF
        else:
            addr_inv, cmd_inv = (~a_val) & 0x1FFF, (~c_val) & 0xFF
            payload = (a_val << 29) | (addr_inv << 16) | (c_val << 8) | cmd_inv
        bits = [(payload >> i) & 1 for i in range(42)]
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 9000), hdr.get("space_us", 4500)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 560), l1.get("space_us", 1690)] if bit == 1 else [l0.get("mark_us", 560), l0.get("space_us", 560)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 560))

    # --- RCMM GENERATION PATH ---
    elif encoding_type == "rcmm":
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0)
            bit_len = 32 if payload > 0xFFFFFF else (12 if payload <= 0xFFF else 24)
            payload = payload & ((1 << bit_len) - 1)
        else:
            a_val, c_val = addr & 0xFF, cmd & 0xFF
            payload = (a_val << 8) | c_val
            bit_len = 24
        if bit_len not in [12, 24, 32]: bit_len = 24
        bits = [(payload >> i) & 1 for i in range(bit_len - 1, -1, -1)]
        if len(bits) % 2 != 0: bits.insert(0, 0)
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 416), hdr.get("space_us", 277)]
        space_map = {(0, 0): 277, (0, 1): 444, (1, 0): 611, (1, 1): 777}
        for i in range(0, len(bits), 2):
            symbol = (bits[i], bits[i+1])
            single_frame_pulses.append(166)
            single_frame_pulses.append(space_map.get(symbol, 277))
        single_frame_pulses.append(166)

    # --- PANASONIC GENERATION PATH ---
    elif encoding_type == "panasonic":
        c_val = parse_hex(command_hex, 0x00) & 0xFF
        a_val = parse_hex(address_hex, 0x2002)
        manufacturer, system, device = 0x0B02, 0x20, 0x00
        if a_val > 0xFFFF:
            manufacturer, system, device = (a_val >> 16) & 0xFFFF, (a_val >> 8) & 0xFF, a_val & 0xFF
        elif a_val > 0xFF:
            system, device = (a_val >> 8) & 0xFF, a_val & 0xFF
        else:
            system = a_val & 0xFF
        if payload_hex and str(payload_hex).strip():
            custom_pay = parse_hex(payload_hex, 0) & 0xFFFFFFFFFFFF
            manufacturer, system, device, c_val = (custom_pay >> 32) & 0xFFFF, (custom_pay >> 24) & 0xFF, (custom_pay >> 16) & 0xFF, (custom_pay >> 8) & 0xFF
        checksum = system ^ device ^ c_val
        bytes_arr = [(manufacturer >> 8) & 0xFF, manufacturer & 0xFF, system & 0xFF, device & 0xFF, c_val & 0xFF, checksum & 0xFF]
        bits = []
        def append_byte_lsb(val):
            for i in range(8): bits.append((val >> i) & 1)
        for b in bytes_arr: append_byte_lsb(b)
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 3456), hdr.get("space_us", 1728)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 432), l1.get("space_us", 1296)] if bit == 1 else [l0.get("mark_us", 432), l0.get("space_us", 432)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 432))

    # --- ONKYO GENERATION PATH ---
    elif encoding_type == "onkyo":
        a_val = parse_hex(address_hex, 0x0000) & 0xFFFF
        c_val = parse_hex(command_hex, 0x0000) & 0xFFFF
        bytes_arr = [(a_val >> 8) & 0xFF, a_val & 0xFF, (c_val >> 8) & 0xFF, c_val & 0xFF]
        bits = []
        def append_byte_lsb(val):
            for i in range(8): bits.append((val >> i) & 1)
        for b in bytes_arr: append_byte_lsb(b)
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 9000), hdr.get("space_us", 4500)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 560), l1.get("space_us", 1690)] if bit == 1 else [l0.get("mark_us", 560), l0.get("space_us", 560)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 560))

    # --- LG GENERATION PATH ---
    elif encoding_type == "lg":
        a_val = parse_hex(address_hex, 0x04)
        c_val = parse_hex(command_hex, 0x08)
        use_28_bit = False
        checksum = 0x0
        if payload_hex and str(payload_hex).strip():
            use_28_bit = True
            checksum = parse_hex(payload_hex, 0) & 0xF
        bits = []
        def append_byte_lsb(val):
            for i in range(8): bits.append((val >> i) & 1)
        if use_28_bit or (c_val > 0xFF):
            a_val, c_val = a_val & 0xFF, c_val & 0xFFFF
            append_byte_lsb(a_val)
            append_byte_lsb(c_val & 0xFF)
            append_byte_lsb((c_val >> 8) & 0xFF)
            for i in range(4): bits.append((checksum >> i) & 1)
        else:
            a_val, c_val = a_val & 0xFF, c_val & 0xFF
            append_byte_lsb(a_val)
            append_byte_lsb((~a_val) & 0xFF)
            append_byte_lsb(c_val)
            append_byte_lsb((~c_val) & 0xFF)
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 9000), hdr.get("space_us", 4500)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 560), l1.get("space_us", 1680)] if bit == 1 else [l0.get("mark_us", 560), l0.get("space_us", 560)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 560))

    # --- KASEIKYO GENERATION PATH ---
    elif encoding_type == "kaseikyo":
        if payload_hex and str(payload_hex).strip():
            payload = parse_hex(payload_hex, 0) & 0xFFFFFFFFFFFF
        else:
            a_val = addr & 0xFFFF if address_hex else 0x3200
            c_val = cmd & 0xFFFF if command_hex else 0x00
            payload = (a_val << 32) | (c_val << 16)
        bits = [(payload >> i) & 1 for i in range(48)]
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 3456), hdr.get("space_us", 1728)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 432), l1.get("space_us", 1296)] if bit == 1 else [l0.get("mark_us", 432), l0.get("space_us", 432)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 432))

    # --- JVC GENERATION PATH ---
    elif encoding_type == "jvc":
        a_val, c_val = addr & 0xFF, cmd & 0xFF
        bits = []
        bits.extend([(a_val >> i) & 1 for i in range(8)])
        bits.extend([(c_val >> i) & 1 for i in range(8)])
        hdr = proto.get("header", {})
        single_frame_pulses = [hdr.get("mark_us", 8416), hdr.get("space_us", 4208)]
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 526), l1.get("space_us", 1578)] if bit == 1 else [l0.get("mark_us", 526), l0.get("space_us", 526)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 526))

    # --- DENON GENERATION PATH ---
    elif encoding_type == "denon":
        a_val, c_val = addr & 0x1F, cmd & 0x3FF
        bits = []
        bits.extend([(a_val >> i) & 1 for i in range(5)])
        bits.extend([(c_val >> i) & 1 for i in range(10)])
        l0, l1 = proto.get("logical_0", {}), proto.get("logical_1", {})
        single_frame_pulses = []
        for bit in bits:
            single_frame_pulses.extend([l1.get("mark_us", 275), l1.get("space_us", 1900)] if bit == 1 else [l0.get("mark_us", 275), l0.get("space_us", 775)])
        stop = proto.get("stop_bit", {})
        if stop.get("mark_us", 0) > 0: single_frame_pulses.append(stop.get("mark_us", 275))

    # --- SONY GENERATION PATH ---
    elif encoding_type == "sony":
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
            if i < len(bits) - 1: single_frame_pulses.append(l0.get("space_us", 600))

    # --- NRC17 GENERATION PATH ---
    elif encoding_type == "nrc17":
        T = proto.get("unit_us", 500)
        c_val = cmd & 0xFF
        a_val = addr & 0xF
        sub_val = parse_hex(payload_hex, 0x0) & 0xF
        logical_bits = [1] + [(c_val >> i) & 1 for i in range(8)] + [(a_val >> i) & 1 for i in range(4)] + [(sub_val >> i) & 1 for i in range(4)]
        half_bits = []
        for bit in logical_bits: half_bits.extend([1, 0] if bit == 1 else [0, 1])
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
        addr_4, cmd_8 = addr & 0xF, cmd & 0xFF
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
        if proto.get("stop_bit", {}).get("mark_us", 0) > 0: single_frame_pulses.append(500)

    # --- RC6 MODE 0 GENERATION ---
    elif encoding_type == "rc6":
        T = proto.get("unit_us", 444)
        p_val = parse_hex(payload_hex, -1)
        payload = p_val & 0xFFFF if p_val >= 0 else ((addr & 0xFF) << 8) | (cmd & 0xFF)
        logical_bits = [1, 0, 0, 0, 0] + [(payload >> i) & 1 for i in range(15, -1, -1)]
        t_units = [1, 1, 1, 1, 1, 1, 0, 0]
        for i, bit in enumerate(logical_bits):
            if i == 4: t_units.extend([1, 1, 0, 0] if bit == 1 else [0, 0, 1, 1])
            else: t_units.extend([1, 0] if bit == 1 else [0, 1])
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
        for bit in bits: half_bits.extend([0, 1] if bit == 1 else [1, 0])
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
            if item == "addr": bytes_arr.append(addr & 0xFF)
            elif item == "addr_inv": bytes_arr.append((~addr) & 0xFF)
            elif item == "addr_low": bytes_arr.append(addr & 0xFF)
            elif item == "addr_high": bytes_arr.append((addr >> 8) & 0xFF)
            elif item == "addr_high_inv": bytes_arr.append((~(addr >> 8)) & 0xFF)
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