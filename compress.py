import gzip
import shutil
import os

input_file = 'master_edid_data.json'
output_file = 'master_edid_data.json.gz'

print(f"Compressing {input_file} (This might take a few seconds)...")

if os.path.exists(input_file):
    with open(input_file, 'rb') as f_in:
        with gzip.open(output_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    original_size = os.path.getsize(input_file) / (1024 * 1024)
    compressed_size = os.path.getsize(output_file) / (1024 * 1024)
    
    print("Done! 🎉")
    print(f"Original Size: {original_size:.2f} MB")
    print(f"Compressed Size: {compressed_size:.2f} MB")
else:
    print(f"Error: {input_file} not found.")