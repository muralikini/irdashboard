# encoders/packager.py

def create_raw_bytes(pulses, sample_freq_hz=1000000, file_format="sig"):
    """
    Converts a microsecond Mark/Space timing array into a packed binary bytearray 
    compatible with .SIG, .U1, and .U2 hardware/parser expectations, modulating 
    marks with a 38kHz carrier wave at a 25% battery-optimized duty cycle.
    """
    # 1. Carrier parameters for 38kHz
    frequency_hz = 38000
    period_us = 1000000.0 / frequency_hz  # ~26.315 µs per carrier cycle
    duty_cycle = 0.25                    # 25% duty cycle for battery optimization
    
    # Calculate exact high and low microsecond durations within a single carrier cycle
    carrier_high_us = period_us * duty_cycle          # ~6.58 µs ON
    carrier_low_us = period_us - carrier_high_us      # ~19.73 µs OFF

    # 2. Convert microsecond durations into a modulated 1MHz digital bitstream
    bit_string = ""
    for i, duration in enumerate(pulses):
        is_mark = (i % 2 == 0)  # Even index = Mark (Carrier modulated), Odd index = Space (Low/0)
        
        if is_mark:
            # Modulate the mark duration with the 38kHz carrier wave (25% duty cycle)
            remaining_us = float(duration)
            while remaining_us > 0:
                # Add carrier ON pulse
                h_dur = min(remaining_us, carrier_high_us)
                h_steps = int(round(h_dur))
                bit_string += "1" * h_steps
                remaining_us -= h_dur
                
                if remaining_us <= 0:
                    break
                
                # Add carrier OFF pulse
                l_dur = min(remaining_us, carrier_low_us)
                l_steps = int(round(l_dur))
                bit_string += "0" * l_steps
                remaining_us -= l_dur
        else:
            # Space is continuous low (0)
            count = int(round(duration))
            bit_string += "0" * count

    # 3. Pad to the nearest full byte (8 bits)
    padding = (8 - (len(bit_string) % 8)) % 8
    bit_string += "0" * padding

    # 4. Pack bit string into bytes
    byte_array = bytearray()
    for i in range(0, len(bit_string), 8):
        byte_array.append(int(bit_string[i:i+8], 2))

    # 5. Format-specific header wrappers
    fmt = str(file_format).strip().lower().replace(".", "")
    
    if fmt == "u2":
        header = b"" 
        return header + byte_array
        
    elif fmt == "u1":
        header = b""
        return header + byte_array
        
    else:
        # Standard .SIG raw format packaging
        return byte_array