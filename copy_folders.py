import os
import shutil
from pathlib import Path

def get_zip_files(folder_path):
    """Efficiently get .zip files even from large network folders."""
    path = Path(folder_path)
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Folder does not exist or is not a directory: {folder_path}")

    print("Scanning source folder for ZIP files... (this may take a while on network drives)")
    
    zip_files = []
    count = 0

    # os.scandir is significantly faster than pathlib on network shares
    with os.scandir(folder_path) as entries:
        for entry in entries:
            count += 1
            if count % 2000 == 0:
                print(f"  Scanned {count} items...", end="\r")

            # Fast name check first
            if entry.name.lower().endswith(".zip"):
                # Only call is_file() for candidates that look like zip files
                try:
                    if entry.is_file(follow_symlinks=False):
                        zip_files.append(entry.name)
                except OSError:
                    # Skip files that cannot be accessed
                    continue

    print(f"\nFinished scanning. Found {len(zip_files)} ZIP files.")
    return sorted(zip_files)

def get_folder_names(folder_path):
    path = Path(folder_path)
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Folder does not exist or is not a directory: {folder_path}")
    return {item.name for item in path.iterdir() if item.is_dir()}

def main():
    print("=" * 65)
    print("Copy missing ZIP files (based on folder presence in Destination)")
    print("=" * 65)

    source = input("Enter SOURCE folder path (contains ZIP files): ").strip().strip('"')
    destination = input("Enter DESTINATION folder path (contains folders): ").strip().strip('"')
    third = input("Enter THIRD (target) folder path: ").strip().strip('"')

    Path(third).mkdir(parents=True, exist_ok=True)

    try:
        zip_files = get_zip_files(source)
        dest_folders = get_folder_names(destination)
    except ValueError as e:
        print(f"\nError: {e}")
        return

    # Find ZIP files whose name (without .zip) does NOT exist as a folder
    missing_zips = []
    for zip_name in zip_files:
        folder_name = Path(zip_name).stem
        if folder_name not in dest_folders:
            missing_zips.append(zip_name)

    print(f"\nFound {len(missing_zips)} ZIP file(s) that do not have a matching folder in DESTINATION.")

    if not missing_zips:
        print("Nothing to copy.")
        return

    print("\nMissing ZIP files:")
    for i, name in enumerate(missing_zips, 1):
        print(f"  {i:3d}. {name}")

    while True:
        try:
            count = int(input(f"\nHow many ZIP files do you want to copy? (1 - {len(missing_zips)}): ").strip())
            if 1 <= count <= len(missing_zips):
                break
            print(f"Please enter a number between 1 and {len(missing_zips)}.")
        except ValueError:
            print("Please enter a valid number.")

    to_copy = missing_zips[:count]

    print(f"\nCopying {len(to_copy)} ZIP file(s) to: {third}")
    print("-" * 65)

    success = 0
    for zip_name in to_copy:
        src_path = Path(source) / zip_name
        dst_path = Path(third) / zip_name

        try:
            if dst_path.exists():
                print(f"  ⚠ Skipped (already exists): {zip_name}")
                continue

            shutil.copy2(src_path, dst_path)
            print(f"  ✓ Copied: {zip_name}")
            success += 1
        except Exception as e:
            print(f"  ✗ Failed: {zip_name} → {e}")

    print("-" * 65)
    print(f"Done. Successfully copied {success} out of {len(to_copy)} ZIP file(s).")

if __name__ == "__main__":
    main()