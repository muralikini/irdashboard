def create_raw_bytes(pulses, sample_freq_hz=1000000, file_format="sig"):
    """
    Converts a microsecond Mark/Space timing array into a packed binary bytearray 
    compatible with .SIG, .U1, and .U2 hardware/parser expectations.
    """
    # 1. Convert microsecond durations to a continuous 1MHz digital bitstream
    bit_string = ""
    for i, duration in enumerate(pulses):
        is_mark = (i % 2 == 0)  # Even index = Mark (High/1), Odd index = Space (Low/0)
        count = int(duration)
        bit_string += ("1" if is_mark else "0") * count

    # 2. Pad to the nearest full byte (8 bits)
    padding = (8 - (len(bit_string) % 8)) % 8
    bit_string += "0" * padding

    # 3. Pack bit string into bytes
    byte_array = bytearray()
    for i in range(0, len(bit_string), 8):
        byte_array.append(int(bit_string[i:i+8], 2))

    # 4. Format-specific header wrappers (safely stripping periods and case)
    fmt = str(file_format).strip().lower().replace(".", "")
    
    if fmt == "u2":
        header = b"" 
        return header + byte_array
    elif fmt == "u1":
        header = b""
        return header + byte_array
    else:
        return byte_array