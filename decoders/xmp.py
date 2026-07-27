# decoders/xmp.py

def decode(pulses):
    """
    Decodes mark/space timings into the XMP protocol.
    XMP encodes a 4-bit nibble into the length of the space.
    """
    if len(pulses) < 16:
        return {"status": "Error", "message": "Signal too short for XMP"}

    def is_tol_abs(val, target, tol=60):
        # Using absolute tolerance because percentage overlaps on tight 138µs steps
        return abs(val - target) <= tol

    nibbles = []
    
    for i in range(0, len(pulses) - 1, 2):
        mark = pulses[i]
        space = pulses[i+1]
        
        # XMP bursts are extremely short, usually ~210µs
        if not is_tol_abs(mark, 210, tol=90):
            return {"status": "Error", "message": f"Invalid XMP Burst at index {i}"}
            
        # Detect frame gaps (usually > 10,000µs)
        if space > 5000:
            break
            
        # Extract the 4-bit nibble from the space duration
        # Formula: Space = 760µs + (nibble * 138µs)
        nibble_found = -1
        for n in range(16):
            target_space = 760 + (n * 138)
            if is_tol_abs(space, target_space, tol=60):
                nibble_found = n
                break
                
        if nibble_found == -1:
            return {"status": "Error", "message": f"Invalid XMP Space at index {i+1}"}
            
        nibbles.append(nibble_found)

    # Convert the array of integers into a continuous hex string
    payload_hex = "".join(f"{n:X}" for n in nibbles)

    return {
        "status": "Success",
        "protocol": "XMP",
        "payload": f"0x{payload_hex}"
    }