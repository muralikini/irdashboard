import os
from signal_parser import RdPlsPython

def convert_file_to_arduino_array(file_path):
    """
    Reads a .sig or .u2 file, parses it using RdPlsPython, 
    and prints a formatted C++ array for Arduino.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    # 1. Initialize parser and process the file (.sig or .u2)
    parser = RdPlsPython(sample_frequency=1.0)
    parser.process_file(file_path)

    # 2. Extract mark/space data
    mark_space_timing = parser.mark_space_data

    if not mark_space_timing:
        print("Error: No mark/space data could be extracted from the file.")
        return

    # 3. Format as C++ unsigned int array
    print(f"\n// Successfully parsed {os.path.basename(file_path)}")
    print(f"// Total pulse transitions: {len(mark_space_timing)}")
    print("unsigned int rawSignal[] = {")
    
    # Format values nicely with line breaks every 10 values
    line = "  "
    for i, val in enumerate(mark_space_timing):
        line += f"{int(val)}, "
        if (i + 1) % 10 == 0:
            print(line)
            line = "  "
    if line.strip():
        print(line)
    print("};")
    print(f"const int rawSignalLength = sizeof(rawSignal) / sizeof(rawSignal[0]);\n")

if __name__ == "__main__":
    # Replace with your actual file path (e.g., 'signal.sig' or 'signal.u2')
    target_file = input("Enter path to your .sig or .u2 file: ").strip().strip('"')
    convert_file_to_arduino_array(target_file)