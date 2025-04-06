# Copyright 2025 Antimortine (antimortine@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import argparse
from pathlib import Path

# --- Configuration ---
ALLOWED_EXTENSIONS = {
    '.md', '.txt', '.py', '.js', '.jsx', '.ts', '.tsx', # Code & Text
    '.css', '.scss', '.html', '.htm',                  # Web Frontend
    '.json', '.yaml', '.yml', '.toml',                 # Config/Data
    '.sh', '.bash', '.zsh',                            # Shell scripts
    'dockerfile', '.dockerignore',                     # Docker (Dockerfiles often have no extension)
    '.gitignore', '.env', '.env.example',             # Other common text files
    '.sql', '.csv',                                    # Data related
    '.xml',                                             # Markup
}
EXCLUDED_DIRS = {
    '.git', 'venv', 'node_modules', '__pycache__', 'build', 'dist',
    'coverage', '.vscode', '.idea', 'chroma_db', '.chroma', 'data',
    'user_projects', # Exclude user data directory
}
EXCLUDED_FILES = {
    'package-lock.json', 'yarn.lock',
}
PATH_SEPARATOR_REPLACEMENT = '___'

# --- End Configuration ---

def is_likely_text_file(file_path: Path) -> bool:
    """Checks if a file is likely text-based by its extension or name."""
    # Check name first for extensionless allowed files (case-insensitive)
    if file_path.name.lower() in ALLOWED_EXTENSIONS:
        return True
    # Check extension (case-insensitive)
    return file_path.suffix.lower() in ALLOWED_EXTENSIONS

def should_process_path(path: Path, source_dir: Path) -> bool:
    """Checks if a file or directory should be processed (not excluded)."""
    try:
        relative_path = path.relative_to(source_dir)
    except ValueError:
        return False # Not relative (e.g., outside symlink)

    # Check against excluded directory names anywhere in the path
    # Using lowercase for case-insensitive comparison
    parts_lower = {part.lower() for part in relative_path.parts}
    if any(part in EXCLUDED_DIRS for part in parts_lower):
        return False

    # Check against excluded filenames (case-insensitive)
    if path.is_file() and path.name.lower() in EXCLUDED_FILES:
        return False

    # Check if it's a file and likely text-based
    if path.is_file() and not is_likely_text_file(path):
        return False

    # If it passed all checks, process it
    return True


def create_flat_copy(source_dir_str: str, target_dir_str: str):
    """
    Copies relevant text files from source_dir to target_dir,
    flattening the structure and renaming files to include
    their original relative path (and original extension) followed by '.txt'.
    """
    source_dir = Path(source_dir_str).resolve()
    target_dir = Path(target_dir_str).resolve()

    if not source_dir.is_dir():
        print(f"Error: Source directory '{source_dir}' not found or is not a directory.")
        return

    if target_dir.exists():
        print(f"Warning: Target directory '{target_dir}' already exists. Clearing it.")
        try:
            shutil.rmtree(target_dir)
        except OSError as e:
            print(f"Error: Could not clear target directory '{target_dir}': {e}")
            return
    try:
        target_dir.mkdir(parents=True, exist_ok=False)
        print(f"Created target directory: '{target_dir}'")
    except OSError as e:
        print(f"Error: Could not create target directory '{target_dir}': {e}")
        return

    copied_files_count = 0
    skipped_files_count = 0
    processed_paths = set() # To handle potential symlink loops or redundant processing

    print(f"Scanning source directory: '{source_dir}'...")

    items_to_process = list(source_dir.rglob('*'))

    for item in items_to_process:
        # Resolve symlinks to check the actual path against exclusions
        try:
            # Important: Resolve links *before* checking processed_paths
            resolved_item = item.resolve()
            # Check if original path or resolved path was already processed
            if item in processed_paths or resolved_item in processed_paths:
                 continue
            processed_paths.add(item) # Mark original path as processed
            if resolved_item != item:
                 processed_paths.add(resolved_item) # Mark resolved path too

        except (OSError, FileNotFoundError) as e: # Handle broken symlinks etc.
            # print(f"Debug: Skipping '{item}' due to resolution error: {e}")
            skipped_files_count += 1
            continue

        # Check if the original path should be processed (respects exclusions based on path name)
        if not should_process_path(item, source_dir):
             if item.is_file() or (item.is_symlink() and not item.is_dir()):
                 skipped_files_count +=1
             continue
        # Also check the resolved path (in case symlink points to excluded type/name)
        # Note: resolved_item might be outside source_dir, should_process_path handles this
        if not should_process_path(resolved_item, source_dir):
             if resolved_item.is_file(): # Only count as skipped file if resolved is file
                  skipped_files_count += 1
             continue


        if resolved_item.is_file(): # Process only if the resolved path is a file
            relative_path = item.relative_to(source_dir) # Use original path for naming

            # Create the base flattened name (path parts joined by separator)
            # This base name INCLUDES the original filename and extension.
            flattened_name_parts = str(relative_path).split(os.sep)
            new_filename_base = PATH_SEPARATOR_REPLACEMENT.join(flattened_name_parts)

            # --- NEW SIMPLIFIED LOGIC ---
            # Append '.txt' to the base name (which includes original extension)
            final_filename = f"{new_filename_base}.txt"
            # --- END NEW LOGIC ---

            target_file_path = target_dir / final_filename

            try:
                # Copy the actual file content from the resolved path
                shutil.copy2(resolved_item, target_file_path) # copy2 preserves metadata
                copied_files_count += 1
            except Exception as e:
                print(f"Error copying file '{resolved_item}' to '{target_file_path}': {e}")
                skipped_files_count += 1
        elif item.is_dir():
             pass # Already handled by rglob implicitly
        else: # Other types
             skipped_files_count += 1

    print("\n--- Processing Complete ---")
    print(f"Source Directory: {source_dir}")
    print(f"Target Directory: {target_dir}")
    print(f"Copied Files (renamed to *.original_ext.txt or *filename.txt): {copied_files_count}")
    print(f"Skipped Items: {skipped_files_count} (includes non-text files, excluded items, broken links)")
    print("--------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Flatten a project directory structure into a single directory, "
                    "copying only specified text files and renaming them to include "
                    "their original relative path (and original extension) "
                    "followed by the .txt extension."
    )
    parser.add_argument(
        "source_dir",
        help="Path to the source project directory (e.g., ./codex-ai)"
    )
    parser.add_argument(
        "target_dir",
        help="Path to the target directory where flattened files will be saved (e.g., ./codex-ai-flat)"
    )

    args = parser.parse_args()

    create_flat_copy(args.source_dir, args.target_dir)