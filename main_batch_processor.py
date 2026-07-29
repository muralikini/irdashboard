# main_batch_processor.py
import os
import json
import glob
from signal_parser import RdPlsPython
from decoders.decoder_registry import try_all_decoders
import legacy_parser

class RemoteFolderProcessor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.map_file = os.path.join(folder_path, "KeySignalMap.txt")
        
    def _parse_metadata(self):
        """Parses UserSelections.json for SIG folders."""
        meta = {}
        for filename in ["UserSelections.json", "UserSelection.json"]:
            filepath = os.path.join(self.folder_path, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        data = json.load(f)
                        meta = {
                            "brand": data.get("Brand", ""),
                            "device": data.get("Device", ""),
                            "subdevice": data.get("Subdevice", ""),
                            "model": data.get("Model", ""),
                            "devicemodel": data.get("Devicemodel", ""),
                            "country": data.get("Country", ""),
                            "region": data.get("Region", "")
                        }
                        break
                except Exception as e:
                    print(f"Error parsing {filepath}: {e}")
        return meta

    def _parse_key_map(self):
        key_map = {}
        if not os.path.exists(self.map_file):
            return key_map
            
        with open(self.map_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                    
                if ':' in line:
                    parts = line.rsplit(':', 1)
                elif ',' in line:
                    parts = line.rsplit(',', 1)
                elif '=' in line:
                    parts = line.rsplit('=', 1)
                else:
                    parts = line.rsplit(None, 1)
                    
                if len(parts) == 2:
                    key_name = parts[0].strip()
                    sig_file = parts[1].strip()
                    if not sig_file.upper().endswith('.SIG'):
                        sig_file += '.SIG'
                    key_map[key_name] = sig_file
        return key_map

    def process(self):
        key_map = self._parse_key_map()
        metadata = self._parse_metadata()
        images = glob.glob(os.path.join(self.folder_path, "*.jpg")) + \
                 glob.glob(os.path.join(self.folder_path, "*.JPG")) + \
                 glob.glob(os.path.join(self.folder_path, "*.png"))
        
        output = {
            "metadata": metadata,
            "reference_images": [os.path.basename(img) for img in images],
            "total_keys_mapped": len(key_map),
            "keys": {}
        }
        
        for key_name, sig_file in key_map.items():
            sig_path = os.path.join(self.folder_path, sig_file)
            if os.path.exists(sig_path):
                processor = RdPlsPython()
                processor.process_file(sig_path)
                
                if not processor.mark_space_data or len(processor.mark_space_data) == 0:
                    decoded_result = {
                        "status": "Error",
                        "message": "Corrupted File (Garbled/Non-Numerical Data)"
                    }
                else:
                    # Target the first segmented frame for primary decoding, fallback to raw flat list
                    target_pulses = processor.frames[0] if processor.frames else processor.mark_space_data
                    decoded_result = try_all_decoders(target_pulses)
                    
                    # Attach multi-frame transmission structure intelligence if successful or repeat
                    if isinstance(decoded_result, dict) and decoded_result.get("status") in ["Success", "Repeat"]:
                        decoded_result["transmission_structure"] = {
                            "frame_count": len(processor.frames),
                            "separators": processor.separators,
                            "has_repeat_frame": len(processor.frames) > 1 or any(s > 15000 for s in processor.separators)
                        }
                    elif isinstance(decoded_result, list):
                        for item in decoded_result:
                            if isinstance(item, dict) and item.get("status") in ["Success", "Repeat"]:
                                item["transmission_structure"] = {
                                    "frame_count": len(processor.frames),
                                    "separators": processor.separators,
                                    "has_repeat_frame": len(processor.frames) > 1 or any(s > 15000 for s in processor.separators)
                                }
                
                output["keys"][key_name] = {
                    "source_file": sig_file,
                    "decode_data": decoded_result
                }
            else:
                output["keys"][key_name] = {
                    "source_file": sig_file,
                    "error": "Signal file missing."
                }
        return output

class LegacyPRJProcessor:
    def __init__(self, folder_path, prj_filename):
        self.folder_path = folder_path
        self.prj_path = os.path.join(folder_path, prj_filename)

    def _parse_prj_header_and_map(self):
        """Parses both header metadata and key mappings from .PRJ text files."""
        meta = {}
        key_map = {}
        try:
            with open(self.prj_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if "CAPTURE LIST" in content:
                header_section, capture_section = content.split("CAPTURE LIST", 1)
            else:
                header_section, capture_section = content, ""

            for line in header_section.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    k = parts[0].strip()
                    v = parts[1].strip()
                    if k == "Brand Name": meta["brand"] = v
                    elif k == "Device Type": meta["device"] = v
                    elif k == "Subdevice Type": meta["subdevice"] = v
                    elif k == "Remote Model": meta["model"] = v
                    elif k == "Target Model": meta["devicemodel"] = v
                    elif k == "Markets": meta["country"] = v

            for line in capture_section.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                parts = line.split(':', 1)
                if len(parts) == 2:
                    sig_file = parts[0].strip()
                    key_name = parts[1].strip()
                    key_map[key_name] = sig_file

        except Exception as e:
            print(f"Error reading PRJ file {self.prj_path}: {e}")
            
        return meta, key_map

    def process(self):
        metadata, key_map = self._parse_prj_header_and_map()
        images = glob.glob(os.path.join(self.folder_path, "*.jpg")) + \
                 glob.glob(os.path.join(self.folder_path, "*.JPG")) + \
                 glob.glob(os.path.join(self.folder_path, "*.png"))
        
        output = {
            "metadata": metadata,
            "reference_images": [os.path.basename(img) for img in images],
            "total_keys_mapped": len(key_map),
            "keys": {}
        }
        
        for key_name, sig_file in key_map.items():
            sig_path = os.path.join(self.folder_path, sig_file)
            if os.path.exists(sig_path):
                mark_space_data = legacy_parser.parse_legacy_file(sig_path)
                
                if not mark_space_data or len(mark_space_data) == 0:
                    decoded_result = {
                        "status": "Error",
                        "message": "Corrupted or Empty Legacy Binary File"
                    }
                else:
                    decoded_result = try_all_decoders(mark_space_data)
                
                output["keys"][key_name] = {
                    "source_file": sig_file,
                    "decode_data": decoded_result
                }
            else:
                output["keys"][key_name] = {
                    "source_file": sig_file,
                    "error": "Signal file missing."
                }
        return output

class BatchRemoteProcessor:
    def __init__(self, root_folder_path, skip_folders=None):
        self.root_folder_path = root_folder_path
        self.skip_folders = skip_folders or set()

    def process_all(self):
        if not os.path.exists(self.root_folder_path):
            return {"error": f"Root folder not found: {self.root_folder_path}"}

        batch_output = {
            "batch_directory": os.path.basename(os.path.normpath(self.root_folder_path)),
            "total_remotes_processed": 0,
            "remotes": {}
        }

        skipped_count = 0

        for item in os.listdir(self.root_folder_path):
            item_path = os.path.join(self.root_folder_path, item)
            
            if os.path.isdir(item_path):
                if item in self.skip_folders:
                    skipped_count += 1
                    continue

                prj_files = [f for f in os.listdir(item_path) if f.upper().endswith('.PRJ')]
                
                if prj_files:
                    print(f"Processing Legacy PRJ/U2 folder: {item}...")
                    processor = LegacyPRJProcessor(item_path, prj_files[0])
                else:
                    print(f"Processing Standard SIG folder: {item}...")
                    processor = RemoteFolderProcessor(item_path)
                
                batch_output["remotes"][item] = processor.process()
                batch_output["total_remotes_processed"] += 1

        if skipped_count > 0:
            print(f"\nSkipped {skipped_count} folders that were already processed in previous runs.")

        return batch_output

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    master_folder = os.path.join(BASE_DIR, "Daily_Captures")
    passed_filename = os.path.join(BASE_DIR, "batch_passed.json")
    failed_filename = os.path.join(BASE_DIR, "batch_failed.json")

    passed_results = {"remotes": {}}
    failed_results = {"remotes": {}}
    processed_folders = set()

    if os.path.exists(passed_filename):
        print(f"Loading existing {passed_filename}...")
        try:
            with open(passed_filename, "r", encoding="utf-8") as f:
                passed_results = json.load(f)
                processed_folders.update(passed_results.get("remotes", {}).keys())
        except Exception as e:
            print(f"Warning: Could not read {passed_filename}: {e}")

    if os.path.exists(failed_filename):
        print(f"Loading existing {failed_filename}...")
        try:
            with open(failed_filename, "r", encoding="utf-8") as f:
                failed_results = json.load(f)
                processed_folders.update(failed_results.get("remotes", {}).keys())
        except Exception as e:
            print(f"Warning: Could not read {failed_filename}: {e}")

    print(f"Total historically processed folders in memory: {len(processed_folders)}")

    pipeline = BatchRemoteProcessor(master_folder, skip_folders=processed_folders)
    batch_json_payload = pipeline.process_all()

    remotes_data = batch_json_payload.get("remotes", {})
    new_passed_count = 0
    new_failed_count = 0

    for remote_name, remote_info in remotes_data.items():
        passed_signals = {}
        failed_signals = {}

        meta = remote_info.get("metadata", {})
        keys_dict = remote_info.get("keys", {})

        for key_name, key_data in keys_dict.items():
            is_success = False
            result = key_data.get("decode_data")

            if result:
                if isinstance(result, list):
                    is_success = any(
                        isinstance(frame, dict) and frame.get("status") in ["Success", "Repeat"]
                        for frame in result
                    )
                elif isinstance(result, dict):
                    is_success = result.get("status") in ["Success", "Repeat"]

            if is_success:
                passed_signals[key_name] = key_data
                new_passed_count += 1
            else:
                failed_signals[key_name] = key_data
                new_failed_count += 1

        if passed_signals:
            passed_results["remotes"][remote_name] = {
                "metadata": meta,
                "keys": passed_signals
            }
        if failed_signals:
            failed_results["remotes"][remote_name] = {
                "metadata": meta,
                "keys": failed_signals
            }

    with open(passed_filename, "w", encoding="utf-8") as f_pass:
        json.dump(passed_results, f_pass, indent=4)

    with open(failed_filename, "w", encoding="utf-8") as f_fail:
        json.dump(failed_results, f_fail, indent=4)

    print(f"\n--- Batch Processing Complete ---")
    print(f" -> Newly processed folders: {len(remotes_data)}")
    print(f" -> Total Passed Folders in Master DB: {len(passed_results['remotes'])}")
    print(f" -> Total Failed Folders in Master DB: {len(failed_results['remotes'])}")