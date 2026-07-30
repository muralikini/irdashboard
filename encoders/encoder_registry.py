# encoders/encoder_registry.py
import json
import os
from encoders import nec, rc5, rc6, rca, sony, apple, bo, denon, jvc, kaseikyo, lg, nrc17, onkyo, panasonic, rcmm, samsung, sanyo, sharp, xmp, zenith

def _get_protocol_definition(proto_upper):
    """Loads master protocol definitions to extract transmission structure rules."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_json_path = os.path.join(base_dir, "..", "protocols_master.json")
    
    if os.path.exists(master_json_path):
        try:
            with open(master_json_path, "r", encoding="utf-8") as f:
                protocols_db = json.load(f)
                return protocols_db.get(proto_upper, {})
        except Exception:
            pass
    return {}

def generate_pulses(protocol, address, command, payload):
    """
    Routes the encoding request to the correct protocol module,
    obtains single-frame pulses, and expands them into multi-frame sequences
    based on master protocol transmission structures.
    """
    proto_upper = str(protocol).strip().upper()
    
    # Extract values, handling empty cells gracefully
    addr = str(address).strip() if address else ""
    cmd = str(command).strip() if command else ""
    pay = str(payload).strip() if payload else ""
    
    # 1. Generate base single-frame pulses using your existing routing logic
    if proto_upper == "NEC":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        single_frame_pulses = nec.encode(addr, cmd)
        
    elif proto_upper == "RC5":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        single_frame_pulses = rc5.encode(addr, cmd)
        
    elif proto_upper == "RC6":
        single_frame_pulses = rc6.encode(addr, cmd, pay)
        
    elif proto_upper == "RCA":
        addr = addr or "0x0"
        cmd = cmd or "0x00"
        single_frame_pulses = rca.encode(addr, cmd)
        
    elif proto_upper == "SONY":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        single_frame_pulses = sony.encode(addr, cmd, pay)
        
    elif proto_upper == "APPLE":
        single_frame_pulses = apple.encode(addr, cmd, pay)
        
    elif proto_upper in ["BO", "BANG & OLUFSEN"]:
        single_frame_pulses = bo.encode(addr, cmd, pay)
        
    elif proto_upper == "DENON":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        single_frame_pulses = denon.encode(addr, cmd)
        
    elif proto_upper == "JVC":
        addr = addr or "0x00"
        cmd = cmd or "0x00"
        single_frame_pulses = jvc.encode(addr, cmd)
        
    elif proto_upper in ["KASEIKYO", "KASEIKYO (GENERIC)"]:
        single_frame_pulses = kaseikyo.encode(addr, cmd, pay)
        
    elif proto_upper in ["LG", "LG 32-BIT", "LG 28-BIT"]:
        single_frame_pulses = lg.encode(addr, cmd, pay)
        
    elif proto_upper in ["NRC17", "NOKIA NRC17"]:
        single_frame_pulses = nrc17.encode(addr, cmd, pay)
        
    elif proto_upper == "ONKYO":
        addr = addr or "0x0000"
        cmd = cmd or "0x0000"
        single_frame_pulses = onkyo.encode(addr, cmd, pay)
        
    elif proto_upper == "PANASONIC":
        single_frame_pulses = panasonic.encode(addr, cmd, pay)
        
    elif proto_upper in ["RCMM", "RC-MM"]:
        single_frame_pulses = rcmm.encode(addr, cmd, pay)
        
    elif proto_upper in ["SAMSUNG", "SAMSUNG/RCA-32 VARIANT"]:
        single_frame_pulses = samsung.encode(addr, cmd, pay)
        
    elif proto_upper in ["SANYO", "SANYO (42-BIT)"]:
        single_frame_pulses = sanyo.encode(addr, cmd, pay)
        
    elif proto_upper == "SHARP":
        single_frame_pulses = sharp.encode(addr, cmd, pay)
        
    elif proto_upper == "XMP":
        single_frame_pulses = xmp.encode(addr, cmd, pay)
        
    elif proto_upper == "ZENITH":
        single_frame_pulses = zenith.encode(addr, cmd, pay)
        
    else:
        raise ValueError(f"Encoder for protocol '{proto_upper}' is not yet implemented.")

    # 2. Lookup multi-frame transmission metadata from the master definitions
    proto_def = _get_protocol_definition(proto_upper)
    struct_meta = proto_def.get("transmission_structure", {})
    
    frame_count = struct_meta.get("frame_count", 1)
    separator_gap = struct_meta.get("separator_gap_us", 40000)
    has_repeat = struct_meta.get("has_repeat_frame", False)
    repeat_def = struct_meta.get("repeat_frame", None)
    
    if frame_count <= 1:
        return single_frame_pulses

    # 3. Build the complete multi-frame pulse train using exact master definition parameters
    multi_frame_pulses = []
    
    if len(single_frame_pulses) % 2 == 0 & proto_upper!="SONY":        
        single_frame_pulses[-1]+=separator_gap
    elif proto_upper!="SONY":
        single_frame_pulses.append(separator_gap)

    for i in range(frame_count):
        multi_frame_pulses.extend(single_frame_pulses)       
        
        #if i < frame_count - 1:
            #if has_repeat and repeat_def:
                # Append the repeat frame definition
                #multi_frame_pulses.extend([
                #    repeat_def.get("mark_us", 9000),
                #    repeat_def.get("space_us", 2250),
                #    repeat_def.get("stop_us", 565)
                #])
                # STRICTLY enforce the master protocol's separator_gap_us here
                
                #multi_frame_pulses.append(separator_gap)
            #else:
                #multi_frame_pulses.append(separator_gap)
                
    return multi_frame_pulses