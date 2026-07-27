# signal_parser.py
import os
import base64

class RdPlsPython:
    """Core Signal Processor: Converts raw .SIG bytes to Mark/Space arrays."""
    def __init__(self, sample_frequency=1.0):
        self.sample_frequency = sample_frequency
        self.raw_data = bytearray()
        self.carrier_data = []
        self.mark_space_data = []

    def process_file(self, filepath):
        """Reads a .SIG file and processes it into mark/space values."""
        with open(filepath, 'rb') as f:
            content = f.read()
            
        # Handle potential legacy text headers
        if b"REMOTE" in content[:20]:
            num_bytes = len(content)
            if num_bytes > (1024 * 16):
                diffbuffer = num_bytes % (16 * 1024)
                self.sample_frequency = 1.0
                self.raw_data = content[diffbuffer:]
            else:
                self.raw_data = content
        else:
            self.raw_data = content

        if len(self.raw_data) > 0:
            self._get_carrier_data(self.raw_data)
            self._get_mark_space_data()

    def _get_carrier_data(self, buffer):
        markval = 0
        spaceval = 0
        prev_bit = 0

        for byte in buffer:
            bits = format(byte, '08b')
            for bit_char in bits:
                current_bit = 1 if bit_char == '1' else 0
                if current_bit == 1:
                    if prev_bit == 1:
                        markval += 1
                    else:
                        self.carrier_data.append(spaceval)
                        spaceval = 0
                        markval += 1
                        prev_bit = 1
                else:
                    if prev_bit == 1:
                        self.carrier_data.append(markval)
                        markval = 0
                        spaceval += 1
                        prev_bit = 0
                    else:
                        spaceval += 1

        if spaceval > 0:
            self.carrier_data.append(spaceval)
        if len(self.carrier_data) > 0:
            self.carrier_data.pop(0)

    def _get_mark_space_data(self):
        prev_space_val = 0.0
        mark = 0.0

        for len_idx, carrier_val in enumerate(self.carrier_data):
            tempval = float(carrier_val)
            if (len_idx % 2) != 0 and prev_space_val != 0:
                if len(str(int(tempval))) >= 3 or tempval >= 50:
                    calc_mark = round((mark + prev_space_val) * self.sample_frequency)
                    self.mark_space_data.append(calc_mark)
                    mark = 0
                    calc_space = round((tempval - prev_space_val) * self.sample_frequency)
                    self.mark_space_data.append(calc_space)
                    prev_space_val = 0
                else:
                    prev_space_val = tempval
                    mark += tempval
            elif (len_idx % 2) != 0 and prev_space_val == 0:
                if len(str(int(tempval))) >= 3 or tempval >= 50:
                    calc_mark = round((mark * self.sample_frequency))
                    self.mark_space_data.append(calc_mark)
                    mark = 0
                    calc_space = round((tempval * self.sample_frequency))
                    self.mark_space_data.append(calc_space)
                    prev_space_val = 0
                else:
                    prev_space_val = tempval
                    mark += tempval
            else:
                mark += tempval

        if mark > 0:
            calc_mark = round((mark + prev_space_val) * self.sample_frequency)
            self.mark_space_data.append(calc_mark)