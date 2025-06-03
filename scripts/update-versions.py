#!/usr/bin/env python3

import json
import sys
import re
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def parse_version(version: str) -> tuple:
    """Parse version string into (major, minor, patch, rc) tuple."""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    major, minor, patch, rc = match.groups()
    return (int(major), int(minor), int(patch), int(rc) if rc else None)

def get_major_version(version: str) -> str:
    """Get major version number."""
    major, *_ = parse_version(version)
    return str(major)

def get_major_minor(version: str) -> str:
    """Get major.minor from version string."""
    major, minor, *_ = parse_version(version)
    return f"{major}.{minor}"

def read_versions_file(filename: str = "versions.json") -> Dict[str, Any]:
    """Read and parse the versions.json file."""
    with open(filename, 'r') as f:
        return json.load(f)

def get_current_major_entry(versions_data: Dict[str, Any], major: str) -> str:
    """Get the latest entry for a given major version."""
    major_entries = [k for k in versions_data.keys() if k.startswith(f"{major}.")]
    if not major_entries:
        return None
    return max(major_entries, key=lambda x: [int(i) for i in x.split('.')])

def get_latest_major_minor(versions_data: Dict[str, Any]) -> str:
    """Get the latest major.minor version from versions.json."""
    return max(versions_data.keys(), key=lambda x: [int(i) for i in x.split('.')])

def update_versions(versions_data: Dict[str, Any], module: str, new_version: str) -> Dict[str, Any]:
    """Update versions.json according to the versioning strategy."""
    if module == 'valkey':
        new_major = get_major_version(new_version)
        new_major_minor = get_major_minor(new_version)
        current_entry = get_current_major_entry(versions_data, new_major)
        
        if current_entry is None:
            # Only create new entry for new major version
            current_major_minor = get_latest_major_minor(versions_data)
            # Create new entry in a new dict to preserve order
            new_entry = {
                "version": new_version,
                "valkey-server": {
                    "version": new_version
                },
                "modules": {
                    "valkey-json": versions_data[current_major_minor]["modules"]["valkey-json"].copy(),
                    "valkey-bloom": versions_data[current_major_minor]["modules"]["valkey-bloom"].copy(),
                    "valkey-search": versions_data[current_major_minor]["modules"]["valkey-search"].copy()
                }
            }
            # Add new entry while preserving order
            versions_data[new_major_minor] = new_entry
            return versions_data
        else:
            # Update within existing major version
            if new_major_minor != current_entry:
                # New minor version within same major - preserve order while updating key
                result = {}
                for k, v in versions_data.items():
                    if k == current_entry:
                        result[new_major_minor] = v  # Add with new key
                    else:
                        result[k] = v  # Keep other entries as is
                versions_data = result
            
            # Update versions
            versions_data[new_major_minor]["version"] = new_version
            versions_data[new_major_minor]["valkey-server"]["version"] = new_version
            return versions_data
    else:
        # Handle module updates
        module_name = f"valkey-{module}"
        current_major_minor = get_latest_major_minor(versions_data)
        
        if module_name in versions_data[current_major_minor]["modules"]:
            versions_data[current_major_minor]["modules"][module_name]["version"] = new_version
        else:
            logging.error(f"Unknown module: {module}")
            return versions_data

    return versions_data

if __name__ == "__main__":
    if len(sys.argv) != 4:
        logging.error("Usage: update_versions.py <json_file> <module> <new_version>")
        sys.exit(1)

    json_file = sys.argv[1]
    module = sys.argv[2]
    new_version = sys.argv[3]

    try:
        versions_data = read_versions_file(json_file)
    except FileNotFoundError:
        logging.error(f"Error: {json_file} not found")
        sys.exit(1)

    # Update versions
    updated_data = update_versions(versions_data, module, new_version)

    # Write updated JSON
    with open(json_file, 'w') as f:
        json.dump(updated_data, f, indent=2)
        f.write('\n')

    logging.info(f"Successfully updated {module} to version {new_version}")
