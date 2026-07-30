import os
import math

class RdPlsPython:
    def __init__(self, signal_path):
        self.signal_file_path = signal_path
        self.sample_frequency = 1.0  # Default for .SIG and .U2 files
        self.raw_data = None
        self.carrier_data = []
        self.mark_space_data = []
        self.original_signal = ""

    def process_ir_signal(self):
        """Reads the signal file, removes headers if present, extracts carrier info, and builds mark-space data."""
        if not os.path.exists(self.signal_file_path):
            raise FileNotFoundError(f"Signal file not found: {self.signal_file_path}")

        # 1. Read and clean header data (equivalent to FindAndRemoveHeaderData)
        buff = self._find_and_remove_header_data()
        self.raw_data = buff
        
        if len(buff) > 0:
            # 2. Extract carrier data (equivalent to GetCarrierData)
            self._get_carrier_data(buff)
            
            # 3. Convert carrier data to mark-space timing sequence (equivalent to GetMarkSpaceData)
            self._get_mark_space_data()

    def _find_and_remove_header_data(self):
        """Removes legacy text headers if present, otherwise returns raw bytes."""
        with open(self.signal_file_path, "rb") as f:
            full_content = f.read()

        # Check for legacy 'REMOTE' text header in the first line
        try:
            header_snippet = full_content[:100].decode("utf-8", errors="ignore")
            if "REMOTE" in header_snippet:
                num_bytes = len(full_content)
                if num_bytes > (16 * 1024):
                    diff_buffer = num_bytes % (16 * 1024)
                    buff = full_content[diff_buffer:]
                    self.sample_frequency = 1.0
                    return bytearray(buff)
        except Exception:
            pass

        # Standard file read path for .SIG / .U2
        buff = bytearray(full_content)
        if len(buff) > 0:
            import base64
            self.original_signal = base64.b64encode(bytes(buff)).decode("utf-8")
        return buff

    def _get_carrier_data(self, buffer):
        """Extracts carrier mark and space durations from raw byte buffer bit by bit."""
        markval = 0
        spaceval = 0
        prev_bit = 0
        self.carrier_data = []

        for b in buffer:
            # Extract bits from MSB (7) down to LSB (0) matching C# BitArray order
            for i in range(7, -1, -1):
                bit_val = (b >> i) & 1
                
                if bit_val == 1:
                    if prev_bit == 1:
                        markval += 1
                    else:  # Transition from 0 to 1
                        self.carrier_data.append(spaceval)
                        spaceval = 0
                        markval += 1
                        prev_bit = 1
                else:  # bit_val == 0
                    if prev_bit == 1:  # Transition from 1 to 0
                        self.carrier_data.append(markval)
                        markval = 0
                        spaceval += 1
                        prev_bit = 0
                    else:
                        spaceval += 1
                        prev_bit = 0

        if spaceval > 0:
            self.carrier_data.append(spaceval)

        # Remove the initial padding element matching C# logic
        if len(self.carrier_data) > 0:
            self.carrier_data.pop(0)

    def _get_mark_space_data(self):
        """Converts raw carrier mark/space alternations into clean timing pulses."""
        prev_space_val = 0
        mark = 0
        tolerance = 4
        self.mark_space_data = []

        for idx, val in enumerate(self.carrier_data):
            temp_val = float(val)
            
            # Check if it is an odd index (space / gap element)
            if idx % 2 != 0 and prev_space_val != 0:
                if len(str(int(temp_val))) >= 3 or temp_val >= 50:
                    # Append Mark element
                    m_val = round((mark + prev_space_val) * self.sample_frequency)
                    self.mark_space_data.append(m_val)
                    
                    # Append Space element
                    s_val = round((temp_val - prev_space_val) * self.sample_frequency)
                    self.mark_space_data.append(s_val)
                    
                    prev_space_val = 0
                    mark = 0
                else:
                    prev_space_val = temp_val
                    mark += temp_val
            elif idx % 2 != 0 and prev_space_val == 0:
                if len(str(int(temp_val))) >= 3 or temp_val >= 50:
                    m_val = round(mark * self.sample_frequency)
                    self.mark_space_data.append(m_val)
                    
                    s_val = round(temp_val * self.sample_frequency)
                    self.mark_space_data.append(s_val)
                    
                    prev_space_val = 0
                    mark = 0
                else:
                    prev_space_val = temp_val
                    mark += temp_val
            else:
                # Even index (Ton / Mark burst component)
                mark += temp_val

        if mark > 0:
            m_val = round((mark + prev_space_val) * self.sample_frequency)
            self.mark_space_data.append(m_val)

# --- Example Usage ---
if __name__ == "__main__":
    # Test path pointing to your capture file
    file_path = os.path.join(os.path.dirname(__file__), "AC_Captures", "AC129", "639107477229169738.SIG")
    
    decoder = RdPlsPython(file_path)
    decoder.process_ir_signal()
    
    print(f"Total Mark-Space elements extracted: {len(decoder.mark_space_data)}")
    print(f"First 20 Mark-Space timings: {decoder.mark_space_data[:20]}")