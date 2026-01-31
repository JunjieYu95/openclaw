#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=10.0.0",
# ]
# ///
"""
WeChat Local Data Access Validation

Since WeChat runs on your machine, the data MUST exist locally:
- SQLite databases (messages, contacts, moments cache)
- Plist files (settings, account info)
- Cache files (media, thumbnails)
- Memory (if process is running)

This script explores direct data access without UI automation.

Usage:
    uv run validate_local_data.py [--deep-scan] [--dump-structure]
"""

import argparse
import json
import os
import plistlib
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# WeChat data locations on macOS
WECHAT_CONTAINERS = [
    Path.home() / "Library/Containers/com.tencent.xinWeChat",
    Path.home() / "Library/Group Containers/group.com.tencent.xinWeChat",
]

WECHAT_SUPPORT = Path.home() / "Library/Application Support/com.tencent.xinWeChat"


def find_all_wechat_paths():
    """Find all WeChat-related paths on the system."""
    print("\n" + "=" * 50)
    print("Scanning for WeChat Data Locations")
    print("=" * 50)

    found_paths = []

    # Check container paths
    for container in WECHAT_CONTAINERS:
        if container.exists():
            print(f"\n[FOUND] {container}")
            found_paths.append(container)

            # List top-level contents
            try:
                for item in sorted(container.iterdir())[:10]:
                    size = get_dir_size(item) if item.is_dir() else item.stat().st_size
                    print(f"  - {item.name} ({format_size(size)})")
            except PermissionError:
                print("  (permission denied)")

    # Check Application Support
    if WECHAT_SUPPORT.exists():
        print(f"\n[FOUND] {WECHAT_SUPPORT}")
        found_paths.append(WECHAT_SUPPORT)

    # Search for any wechat-related in Library
    library = Path.home() / "Library"
    for subdir in ["Caches", "Preferences", "Saved Application State"]:
        path = library / subdir
        if path.exists():
            for item in path.iterdir():
                if "wechat" in item.name.lower() or "tencent" in item.name.lower():
                    print(f"\n[FOUND] {item}")
                    found_paths.append(item)

    return found_paths


def get_dir_size(path: Path) -> int:
    """Get total size of directory."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except:
        pass
    return total


def format_size(size: int) -> str:
    """Format size in human readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def find_databases(base_paths: list[Path]):
    """Find all database files."""
    print("\n" + "=" * 50)
    print("Searching for Database Files")
    print("=" * 50)

    db_files = []
    patterns = ["*.db", "*.sqlite", "*.sqlite3", "*WCDB*", "*MSG*", "*Contact*", "*SNS*"]

    for base in base_paths:
        for pattern in patterns:
            for db in base.rglob(pattern):
                if db.is_file():
                    db_files.append(db)

    # Deduplicate and sort by size
    db_files = list(set(db_files))
    db_files.sort(key=lambda x: x.stat().st_size, reverse=True)

    print(f"\nFound {len(db_files)} database files:")
    for db in db_files[:20]:
        size = db.stat().st_size
        print(f"  {format_size(size):>10}  {db.name}")
        print(f"             {db.parent}")

    return db_files


def analyze_database(db_path: Path):
    """Try to analyze a database file."""
    print(f"\n" + "-" * 50)
    print(f"Analyzing: {db_path.name}")
    print("-" * 50)

    try:
        # Check if it's a valid SQLite file
        with open(db_path, 'rb') as f:
            header = f.read(16)

        if header[:6] == b'SQLite':
            print("Format: Standard SQLite")

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Tables ({len(tables)}): {tables[:10]}")

            # Sample data from first few tables
            for table in tables[:3]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    count = cursor.fetchone()[0]
                    print(f"  {table}: {count} rows")

                    # Get columns
                    cursor.execute(f"PRAGMA table_info([{table}])")
                    columns = [row[1] for row in cursor.fetchall()]
                    print(f"    Columns: {columns[:5]}...")

                except Exception as e:
                    print(f"  {table}: error - {e}")

            conn.close()
            return {"type": "sqlite", "tables": tables}

        elif b'WCDB' in header or header[:4] == b'\x00\x00\x00\x00':
            print("Format: WCDB (WeChat encrypted database)")
            print("Status: Encrypted - key extraction needed")
            return {"type": "wcdb_encrypted"}

        else:
            print(f"Format: Unknown (header: {header[:8]})")
            return {"type": "unknown"}

    except sqlite3.DatabaseError as e:
        if "encrypted" in str(e).lower() or "not a database" in str(e).lower():
            print("Format: Encrypted or corrupted")
            return {"type": "encrypted"}
        print(f"SQLite error: {e}")
        return {"type": "error", "error": str(e)}

    except Exception as e:
        print(f"Error: {e}")
        return {"type": "error", "error": str(e)}


def find_plist_files(base_paths: list[Path]):
    """Find and read plist files (often unencrypted config/cache)."""
    print("\n" + "=" * 50)
    print("Searching for Plist Files (config/cache)")
    print("=" * 50)

    plist_files = []

    for base in base_paths:
        for plist in base.rglob("*.plist"):
            if plist.is_file():
                plist_files.append(plist)

    print(f"Found {len(plist_files)} plist files")

    interesting_data = {}

    for plist_path in plist_files[:20]:
        try:
            with open(plist_path, 'rb') as f:
                data = plistlib.load(f)

            # Look for interesting keys
            if isinstance(data, dict):
                interesting_keys = [k for k in data.keys() if any(
                    term in k.lower() for term in ['user', 'account', 'id', 'name', 'token', 'key', 'wxid']
                )]

                if interesting_keys:
                    print(f"\n{plist_path.name}:")
                    for key in interesting_keys[:5]:
                        value = data[key]
                        if isinstance(value, (str, int, float)):
                            # Truncate long values
                            val_str = str(value)[:50]
                            print(f"  {key}: {val_str}")
                        else:
                            print(f"  {key}: <{type(value).__name__}>")

                    interesting_data[str(plist_path)] = {k: data[k] for k in interesting_keys}

        except Exception as e:
            continue

    return interesting_data


def find_cache_files(base_paths: list[Path]):
    """Find cache files that might contain readable data."""
    print("\n" + "=" * 50)
    print("Searching for Cache/Data Files")
    print("=" * 50)

    cache_patterns = {
        "images": ["*.jpg", "*.jpeg", "*.png", "*.gif"],
        "video": ["*.mp4", "*.mov"],
        "audio": ["*.mp3", "*.wav", "*.amr"],
        "json": ["*.json"],
        "xml": ["*.xml"],
        "data": ["*.dat", "*.data"],
    }

    file_counts = {}

    for base in base_paths:
        for category, patterns in cache_patterns.items():
            count = 0
            sample = None
            for pattern in patterns:
                files = list(base.rglob(pattern))
                count += len(files)
                if files and not sample:
                    sample = files[0]

            if count > 0:
                if category not in file_counts:
                    file_counts[category] = {"count": 0, "sample": None}
                file_counts[category]["count"] += count
                if sample:
                    file_counts[category]["sample"] = sample

    print("\nCache file summary:")
    for category, info in file_counts.items():
        print(f"  {category}: {info['count']} files")
        if info['sample']:
            print(f"    Sample: {info['sample']}")

    return file_counts


def find_moments_data(base_paths: list[Path]):
    """Specifically look for Moments/SNS data."""
    print("\n" + "=" * 50)
    print("Searching for Moments (朋友圈/SNS) Data")
    print("=" * 50)

    moments_indicators = ['sns', 'moment', 'timeline', 'pyq', 'friend', 'circle']

    for base in base_paths:
        for item in base.rglob("*"):
            name_lower = item.name.lower()
            if any(ind in name_lower for ind in moments_indicators):
                if item.is_file():
                    print(f"[FILE] {item} ({format_size(item.stat().st_size)})")
                else:
                    print(f"[DIR]  {item}")
                    # List contents
                    try:
                        contents = list(item.iterdir())[:5]
                        for c in contents:
                            print(f"       - {c.name}")
                    except:
                        pass


def check_memory_access():
    """Check if we can access WeChat process memory."""
    print("\n" + "=" * 50)
    print("Process Memory Access Check")
    print("=" * 50)

    # Find WeChat PID
    result = subprocess.run(["pgrep", "-x", "WeChat"], capture_output=True, text=True)

    if result.returncode != 0:
        print("WeChat not running")
        return False

    pid = result.stdout.strip().split('\n')[0]
    print(f"WeChat PID: {pid}")

    # Check if we can access process info
    try:
        # Get memory map
        result = subprocess.run(
            ["vmmap", pid],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.split('\n')
            print(f"Memory regions: {len(lines)} lines")

            # Look for interesting regions
            for line in lines[:20]:
                if any(term in line.lower() for term in ['wechat', 'sqlite', 'db']):
                    print(f"  {line[:80]}")

            return True
        else:
            print(f"vmmap failed: {result.stderr[:100]}")
            return False

    except subprocess.TimeoutExpired:
        print("vmmap timed out")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def try_extract_key_from_memory():
    """Attempt to find database encryption key in memory."""
    print("\n" + "-" * 50)
    print("Encryption Key Search (experimental)")
    print("-" * 50)

    print("""
WCDB Encryption Key Extraction:
─────────────────────────────────
WeChat uses WCDB with SQLCipher encryption. The key is typically:
1. Derived from device ID + user ID
2. Stored in Keychain
3. Loaded into memory when WeChat runs

Methods to obtain key:
a) Keychain access (requires password or TouchID)
b) Memory dump analysis (requires debugging permissions)
c) Hooking WeChat's key loading function (requires SIP disabled)

For legitimate personal use, Keychain is the cleanest approach.
""")

    # Try to find in Keychain
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "com.tencent.xinWeChat", "-w"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Found WeChat keychain entry!")
            # Don't print the actual key
            return True
        else:
            print("No direct keychain entry found (may need specific label)")

    except Exception as e:
        print(f"Keychain search error: {e}")

    return False


def generate_report(results: dict):
    """Generate findings report."""
    print("\n" + "=" * 50)
    print("LOCAL DATA ACCESS REPORT")
    print("=" * 50)

    print("""
FINDINGS SUMMARY:
─────────────────
""")

    if results.get('databases'):
        print(f"Databases found: {len(results['databases'])}")
        encrypted = sum(1 for db in results.get('db_analysis', []) if 'encrypt' in str(db).lower())
        print(f"  - Encrypted (WCDB): {encrypted}")
        print(f"  - Potentially readable: {len(results['databases']) - encrypted}")

    if results.get('plists'):
        print(f"\nPlist files with user data: {len(results['plists'])}")

    if results.get('cache'):
        total_cache = sum(info['count'] for info in results['cache'].values())
        print(f"\nCache files: {total_cache}")

    print("""

RECOMMENDED APPROACH:
─────────────────────
1. CHECK FOR UNENCRYPTED DATABASES
   Some auxiliary databases may not be encrypted.
   These could contain contacts, recent messages preview, etc.

2. PLIST DATA EXTRACTION
   Plist files often contain account info, settings,
   and cached data in readable format.

3. CACHE FILE PARSING
   Media cache (images, voice) is typically unencrypted.
   Thumbnails and previews may be directly readable.

4. WCDB KEY EXTRACTION (if needed)
   - Use Keychain Access app to find WeChat keys
   - Or use memory analysis tools with debugging enabled

5. SQLITE-WCDB BRIDGE
   Once key is obtained, WCDB databases can be decrypted
   and read like normal SQLite.

NEXT STEP:
──────────
Run with --deep-scan to analyze all found databases
and identify which ones are readable.
""")


def main():
    parser = argparse.ArgumentParser(
        description="Explore WeChat local data access"
    )
    parser.add_argument(
        "--deep-scan", "-d",
        action="store_true",
        help="Deep scan and analyze all databases"
    )
    parser.add_argument(
        "--dump-structure", "-s",
        action="store_true",
        help="Dump full directory structure"
    )
    parser.add_argument(
        "--check-memory", "-m",
        action="store_true",
        help="Check process memory access"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChat Local Data Access Validation")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nExploring direct data access (no UI automation)")

    results = {}

    # Find all WeChat paths
    base_paths = find_all_wechat_paths()

    if not base_paths:
        print("\nNo WeChat data directories found!")
        print("Make sure WeChat is installed and has been used.")
        sys.exit(1)

    # Find databases
    results['databases'] = find_databases(base_paths)

    # Analyze databases if deep scan
    if args.deep_scan and results['databases']:
        results['db_analysis'] = []
        for db in results['databases'][:10]:  # Analyze top 10 by size
            analysis = analyze_database(db)
            results['db_analysis'].append(analysis)

    # Find plist files
    results['plists'] = find_plist_files(base_paths)

    # Find cache files
    results['cache'] = find_cache_files(base_paths)

    # Look for Moments specifically
    find_moments_data(base_paths)

    # Check memory access
    if args.check_memory:
        results['memory'] = check_memory_access()
        try_extract_key_from_memory()

    # Generate report
    generate_report(results)


if __name__ == "__main__":
    main()
