# encoders/packager.py

def create_raw_bytes(pulses, sample_freq_hz=1000000):
    """
    Converts a Mark/Space array into raw binary bytes based on a sample frequency.
    At 1 MHz, 1 microsecond = 1 sample (1 bit).
    """
    bit_string = []
    is_mark = True  # IR signals always begin with a Mark (burst)
    
    # 1. Generate the raw stream of 1s (Marks) and 0s (Spaces)
    for duration_us in pulses:
        # Calculate exactly how many bits this pulse consumes at the given frequency
        samples = int(round(duration_us * (sample_freq_hz / 1000000.0)))
        
        # Marks are represented by '1's, Spaces by '0's
        bit = '1' if is_mark else '0'
        bit_string.append(bit * samples)
        
        # Toggle state for the next pulse
        is_mark = not is_mark
        
    full_bits = "".join(bit_string)
    
    # 2. Pad the bit string with '0's so it divides perfectly into 8-bit bytes
    remainder = len(full_bits) % 8
    if remainder != 0:
        full_bits += '0' * (8 - remainder)
        
    # 3. Convert the continuous bitstream into actual byte values (MSB first)
    byte_array = bytearray()
    for i in range(0, len(full_bits), 8):
        byte_val = int(full_bits[i:i+8], 2)
        byte_array.append(byte_val)
        
    return bytes(byte_array)