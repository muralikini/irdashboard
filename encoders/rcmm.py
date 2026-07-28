# encoders/rcmm.py

def encode(address_hex, command_hex, payload_hex=""):
    """
    Encodes Philips RC-MM protocol fields into a Mark/Space timing array 
    using Pulse Position Modulation (2 bits per symbol).
    """
    
    # 1. Determine the payload value (Defaults to 24-bit if not specified)
    if payload_hex and str(payload_hex).strip():
        payload = int(str(payload_hex), 16)
        # Auto-detect bit length based on value magnitude if not strictly defined
        bit_len = 32 if payload > 0xFFFFFF else (12 if payload <= 0xFFF else 24)
        payload = payload & ((1 << bit_len) - 1)
    else:
        addr = int(str(address_hex), 16) if address_hex else 0x00
        cmd = int(str(command_hex), 16) if command_hex else 0x00
        # Combine into a standard 24-bit payload structure (Address + Command)
        payload = (addr << 8) | cmd
        bit_len = 24

    # Ensure valid bit length (12, 24, or 32)
    if bit_len not in [12, 24, 32]:
        bit_len = 24

    # 2. Extract pairs of bits (MSB first)
    bits = [(payload >> i) & 1 for i in range(bit_len - 1, -1, -1)]
    
    # Pad to even number of bits if necessary for symbol grouping
    if len(bits) % 2 != 0:
        bits.insert(0, 0)

    # 3. RC-MM Header: 416µs Mark, 277µs Space[cite: 16]
    pulses = [416, 277]

    # Map 2-bit symbols to their respective space durations[cite: 16]
    # 00 -> 277µs, 01 -> 444µs, 10 -> 611µs, 11 -> 777µs
    space_map = {
        (0, 0): 277,
        (0, 1): 444,
        (1, 0): 611,
        (1, 1): 777
    }

    # 4. Convert bit pairs into Mark/Space timing pairs
    for i in range(0, len(bits), 2):
        symbol = (bits[i], bits[i+1])
        pulses.append(166)  # Mark is always strictly ~166µs[cite: 16]
        pulses.append(space_map.get(symbol, 277))

    # Append final stop mark to terminate the sequence
    pulses.append(166)

    return pulses