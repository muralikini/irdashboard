# decoders/nrc17.py

def decode(pulses, tolerance=0.25):
    """
    Decodes mark/space timings into Nokia NRC17 protocol fields.
    Payload structure: 17 bits (1 Start, 8 Command, 4 Address, 4 Subcode).
    """
    T = 500  # Basic time unit (half-bit) in microseconds

    # An NRC17 transmission requires a header and at least some payload pulses
    if len(pulses) < 18:
        return {"status": "Error", "message": "Signal too short for NRC17"}

    def is_tol(val, target):
        return abs(val - target) <= (target * tolerance)

    # 1. Header Validation (500µs mark, 2500µs space)
    if not (is_tol(pulses[0], 1 * T) and is_tol(pulses[1], 5 * T)):
        return {"status": "Error", "message": "Invalid NRC17 Header"}

    # 2. Convert remaining physical pulses into 't-units'
    t_units_list = []
    current_level = 1  # Next signal after the header space must be a Mark

    for duration in pulses[2:]:
        units = int(round(duration / float(T)))
        
        # Max duration for Manchester is 2t (except the header, which is already handled)
        if units == 0 or units > 2:
            return {"status": "Error", "message": f"Invalid NRC17 interval: {duration}µs"}
            
        t_units_list.extend([current_level] * units)
        current_level = 1 - current_level

    # Ensure we have enough t-units to parse 17 bits (34 half-bits)
    if len(t_units_list) < 34:
        # If the last bit was '1' (Mark -> Space), the trailing space might not be captured
        # by the receiver as it is just silence. We pad it if it is missing.
        if len(t_units_list) == 33 and t_units_list[-1] == 1:
            t_units_list.append(0)
        else:
            return {"status": "Error", "message": "Signal too short for full NRC17 Payload"}

    # 3. Parse Bits (Manchester: [1, 0] -> '1'; [0, 1] -> '0')
    bits = []
    for i in range(0, 34, 2):
        pair = t_units_list[i:i+2]
        if pair == [1, 0]:
            bits.append(1)
        elif pair == [0, 1]:
            bits.append(0)
        else:
            return {"status": "Error", "message": f"Manchester violation at bit {i//2}"}

    # 4. Extract NRC17 Fields
    start_bit = bits[0]
    if start_bit != 1:
        return {"status": "Error", "message": "Invalid NRC17 Start Bit"}

    # Command (8 bits, LSB first)
    command_bits = bits[1:9]
    command_bits.reverse()
    command_val = int("".join(map(str, command_bits)), 2)

    # Address (4 bits, LSB first)
    address_bits = bits[9:13]
    address_bits.reverse()
    address_val = int("".join(map(str, address_bits)), 2)

    # Subcode (4 bits, LSB first)
    subcode_bits = bits[13:17]
    subcode_bits.reverse()
    subcode_val = int("".join(map(str, subcode_bits)), 2)

    return {
        "status": "Success",
        "protocol": "NRC17",
        "command": hex(command_val),
        "address": hex(address_val),
        "subcode": hex(subcode_val)
    }