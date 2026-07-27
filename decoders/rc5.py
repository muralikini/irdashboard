# decoders/rc5.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Philips RC5 protocol fields using Manchester decoding.
    Payload structure: 14 bits (2 Start, 1 Toggle, 5 Address, 6 Command).
    """

    # --- NEW SAFETY CHECK ---
    # Fails safely if the .SIG file was empty or corrupted
    if not pulses or len(pulses) == 0:
        return {"status": "Error", "message": "Signal is empty"}

    # ------------------------
    
    T = 889  # The standard RC5 half-bit duration in microseconds

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # In RC5, the first bit is a '1' (Space -> Mark).
    # Because IR receivers don't capture the initial Space, the very first 
    # signal we receive is the second half of the Start bit (an 889µs Mark).
    if not is_tol(pulses[0], T):
        return {"status": "Error", "message": "Invalid RC5 starting mark"}

    # Reconstruct the half-bits (1 = Mark, 0 = Space)
    half_bits = [0]  # Prepend the invisible first space
    current_level = 1

    for duration in pulses:
        # A duration of ~889µs equals 1 half-bit
        if is_tol(duration, T):
            half_bits.append(current_level)
        # A duration of ~1778µs equals 2 half-bits of the same level
        elif is_tol(duration, 2 * T):
            half_bits.extend([current_level, current_level])
        else:
            return {"status": "Error", "message": f"Invalid Manchester duration: {duration}µs"}
        
        # Toggle the physical IR level (Mark -> Space -> Mark)
        current_level = 1 - current_level

    # If the final bit was a '0' (Mark -> Space), the IR receiver may not capture 
    # the final Space because it's just silence. We pad it if it's missing.
    if len(half_bits) == 27:
        half_bits.append(0)

    if len(half_bits) < 28:
        return {"status": "Error", "message": "Signal too short for full RC5"}
    
    # We only care about the first 28 half-bits (14 full bits)
    half_bits = half_bits[:28]

    # Pair the half-bits back into logical bits
    bits = []
    for i in range(0, 28, 2):
        pair = (half_bits[i], half_bits[i+1])
        if pair == (0, 1):
            bits.append(1)
        elif pair == (1, 0):
            bits.append(0)
        else:
            return {"status": "Error", "message": f"Manchester violation at bit {i//2}"}

    # Extract RC5 Fields
    s1 = bits[0]
    s2 = bits[1]
    toggle = bits[2]
    
    # Address (5 bits, MSB first)
    address_bits = bits[3:8]
    address_val = int("".join(map(str, address_bits)), 2)

    # Command (6 bits, MSB first)
    command_bits = bits[8:14]
    command_val = int("".join(map(str, command_bits)), 2)

    # Extended RC5 Handling:
    # If S2 is '0', Philips extended the command set by adding 64 to the command value.
    if s2 == 0:
        command_val += 64

    return {
        "status": "Success",
        "protocol": "RC5",
        "address": hex(address_val),
        "command": hex(command_val),
        "toggle": toggle
    }