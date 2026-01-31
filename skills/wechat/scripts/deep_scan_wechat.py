#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Deep scan for WeChat data files.

The previous scan found mostly WebKit databases.
This script does a thorough scan to find the actual WeChat data:
- WCDB encrypted databases (check file headers)
- Binary data files
- Protobuf/binary message stores
- Account-specific directories

Usage:
    uv run deep_scan_wechat.py
"""

import os
import sqlite3
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path


WECHAT_PATHS = [
    Path.home() / "Library/Containers/com.tencent.xinWeChat",
    Path.home() / "Library/Group Containers/group.com.tencent.xinWeChat",
    Path.home() / "Library/Application Support/com.tencent.xinWeChat",
]


def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def check_file_type(filepath: Path) -> dict:
    """Check file type by reading header."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(32)

        info = {"size": filepath.stat().st_size}

        # SQLite standard header
        if header[:6] == b'SQLite':
            info["type"] = "sqlite"
            info["encrypted"] = False
            return info

        # SQLCipher/WCDB encrypted (starts with random bytes, not SQLite header)
        # But has SQLite-like structure
        if len(header) >= 16:
            # Check for WCDB markers
            if b'WCDB' in header or b'wcdb' in header:
                info["type"] = "wcdb"
                info["encrypted"] = True
                return info

        # Check if it might be encrypted SQLite (no header, but .db extension)
        if filepath.suffix.lower() in ['.db', '.sqlite', '.sqlite3']:
            # Try to open as SQLite
            try:
                conn = sqlite3.connect(str(filepath))
                conn.execute("SELECT 1")
                conn.close()
                info["type"] = "sqlite"
                info["encrypted"] = False
            except:
                info["type"] = "encrypted_db"
                info["encrypted"] = True
            return info

        # Protobuf often starts with field tags
        if header[0] in [0x08, 0x0a, 0x10, 0x12, 0x18, 0x1a]:
            info["type"] = "possibly_protobuf"
            return info

        # Binary plist
        if header[:6] == b'bplist':
            info["type"] = "bplist"
            return info

        # XML plist
        if header[:5] == b'<?xml' or b'<plist' in header:
            info["type"] = "xml_plist"
            return info

        # Check for common image formats
        if header[:4] == b'\x89PNG':
            info["type"] = "png"
            return info
        if header[:2] == b'\xff\xd8':
            info["type"] = "jpeg"
            return info

        info["type"] = "binary"
        info["header_hex"] = header[:16].hex()
        return info

    except Exception as e:
        return {"type": "error", "error": str(e)}


def scan_directory_structure(base_path: Path, max_depth: int = 10):
    """Scan directory structure looking for data patterns."""
    print(f"\n{'='*60}")
    print(f"Scanning: {base_path}")
    print('='*60)

    if not base_path.exists():
        print("  Path does not exist")
        return

    # Track findings
    findings = {
        "large_files": [],
        "encrypted_dbs": [],
        "readable_dbs": [],
        "data_dirs": [],
        "interesting_files": [],
    }

    # Walk the directory
    for root, dirs, files in os.walk(base_path):
        root_path = Path(root)
        depth = len(root_path.relative_to(base_path).parts)

        if depth > max_depth:
            continue

        # Check for account/user specific directories (usually hash-like names)
        for d in dirs:
            if len(d) == 32 or len(d) == 64:  # MD5 or SHA256 length
                if all(c in '0123456789abcdef' for c in d.lower()):
                    findings["data_dirs"].append(root_path / d)
                    print(f"\n[USER DATA DIR] {root_path / d}")

        for filename in files:
            filepath = root_path / filename

            try:
                size = filepath.stat().st_size
            except:
                continue

            # Skip tiny files
            if size < 1000:
                continue

            # Check file type
            file_info = check_file_type(filepath)
            file_info["path"] = filepath
            file_info["name"] = filename

            # Large files (> 1MB) are interesting
            if size > 1_000_000:
                findings["large_files"].append(file_info)

            # Database files
            if file_info.get("type") == "encrypted_db" or file_info.get("type") == "wcdb":
                findings["encrypted_dbs"].append(file_info)
                print(f"\n[ENCRYPTED DB] {filepath}")
                print(f"    Size: {format_size(size)}")

            elif file_info.get("type") == "sqlite":
                findings["readable_dbs"].append(file_info)

            # Look for specific WeChat data files
            name_lower = filename.lower()
            if any(kw in name_lower for kw in ['msg', 'message', 'contact', 'sns', 'moment',
                                                'friend', 'chat', 'session', 'fts', 'index']):
                findings["interesting_files"].append(file_info)
                print(f"\n[INTERESTING] {filepath}")
                print(f"    Size: {format_size(size)}, Type: {file_info.get('type')}")

    return findings


def find_account_directories():
    """Find WeChat account-specific directories."""
    print("\n" + "="*60)
    print("Looking for Account Data Directories")
    print("="*60)

    account_dirs = []

    for base in WECHAT_PATHS:
        if not base.exists():
            continue

        # Look for Message directory which contains per-account data
        message_dir = base / "Data/Library/Application Support/com.tencent.xinWeChat/2.0b4.0.9/Message"
        if message_dir.exists():
            print(f"\n[FOUND] Message directory: {message_dir}")
            for item in message_dir.iterdir():
                if item.is_dir():
                    print(f"    Account: {item.name}")
                    account_dirs.append(item)

        # Also check other common paths
        for pattern in ["**/Message/*", "**/Backup/*", "**/DB/*", "**/LocalData/*"]:
            for match in base.glob(pattern):
                if match.is_dir() and match not in account_dirs:
                    # Check if it looks like an account dir
                    files = list(match.iterdir())
                    if any(f.suffix in ['.db', '.data', '.dat'] for f in files if f.is_file()):
                        print(f"\n[DATA DIR] {match}")
                        print(f"    Files: {[f.name for f in files[:5]]}")
                        account_dirs.append(match)

    return account_dirs


def check_macos_wechat_specifics():
    """Check macOS-specific WeChat storage patterns."""
    print("\n" + "="*60)
    print("Checking macOS WeChat Storage Patterns")
    print("="*60)

    # WeChat for Mac stores data differently than mobile
    # Let's find the actual data directory

    container = Path.home() / "Library/Containers/com.tencent.xinWeChat/Data"

    if not container.exists():
        print("WeChat container not found")
        return

    print(f"\nContainer: {container}")

    # List top-level structure
    print("\nTop-level structure:")
    for item in sorted(container.iterdir()):
        if item.is_dir():
            size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            print(f"  [DIR]  {item.name}: {format_size(size)}")
        else:
            print(f"  [FILE] {item.name}: {format_size(item.stat().st_size)}")

    # Look in Library/Application Support
    app_support = container / "Library/Application Support"
    if app_support.exists():
        print(f"\nApplication Support contents:")
        for item in sorted(app_support.iterdir()):
            if item.is_dir():
                subsize = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                print(f"  {item.name}: {format_size(subsize)}")

                # If this is the WeChat data dir, explore further
                if 'wechat' in item.name.lower() or 'tencent' in item.name.lower():
                    for subitem in sorted(item.iterdir())[:10]:
                        print(f"    - {subitem.name}")


def search_for_wcdb_key():
    """Search for WCDB encryption key."""
    print("\n" + "="*60)
    print("Searching for Encryption Key")
    print("="*60)

    # Check Keychain for WeChat entries
    print("\nChecking Keychain for WeChat entries...")
    try:
        result = subprocess.run(
            ["security", "dump-keychain"],
            capture_output=True,
            text=True,
            timeout=30
        )

        lines = result.stdout.split('\n')
        wechat_entries = [l for l in lines if 'wechat' in l.lower() or 'tencent' in l.lower()]

        if wechat_entries:
            print(f"Found {len(wechat_entries)} WeChat-related keychain entries")
            for entry in wechat_entries[:10]:
                print(f"  {entry[:80]}")
        else:
            print("No WeChat entries found in keychain dump")

    except Exception as e:
        print(f"Keychain search error: {e}")

    # Look for key files
    print("\nSearching for key files...")
    for base in WECHAT_PATHS:
        if not base.exists():
            continue
        for keyfile in base.rglob("*key*"):
            if keyfile.is_file():
                print(f"  {keyfile} ({format_size(keyfile.stat().st_size)})")
        for keyfile in base.rglob("*Key*"):
            if keyfile.is_file():
                print(f"  {keyfile} ({format_size(keyfile.stat().st_size)})")


def summarize_findings(all_findings: list):
    """Summarize all findings."""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    total_encrypted = sum(len(f.get("encrypted_dbs", [])) for f in all_findings if f)
    total_readable = sum(len(f.get("readable_dbs", [])) for f in all_findings if f)
    total_large = sum(len(f.get("large_files", [])) for f in all_findings if f)

    print(f"""
Encrypted databases: {total_encrypted}
Readable databases:  {total_readable}
Large files (>1MB):  {total_large}

ANALYSIS:
---------
""")

    if total_encrypted > 0:
        print("""
The main WeChat data appears to be encrypted with WCDB/SQLCipher.

To access this data, we need the encryption key. Options:

1. KEYCHAIN ACCESS
   - Open Keychain Access app
   - Search for "WeChat" or "tencent"
   - Look for encryption keys stored there

2. MEMORY EXTRACTION (requires debugging)
   - Attach debugger to WeChat process
   - Find key in memory when DB is opened
   - Requires disabling SIP (System Integrity Protection)

3. WECHAT EXPORT FEATURE
   - WeChat Mac may have built-in export
   - Check WeChat Settings → General → Data

4. USE WINDOWS VERSION
   - WeChatFerry on Windows can extract the key automatically
   - Run in VM if needed

5. ALTERNATIVE: HOOK INTO WECHAT
   - Create a WeChat plugin/extension
   - Intercept data as it's decrypted
""")
    else:
        print("""
No encrypted databases found in scanned paths.
The data might be in a different location or format.
""")


def main():
    print("="*60)
    print("WeChat Deep Data Scan")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check macOS specifics first
    check_macos_wechat_specifics()

    # Find account directories
    account_dirs = find_account_directories()

    # Scan each base path
    all_findings = []
    for base in WECHAT_PATHS:
        findings = scan_directory_structure(base)
        if findings:
            all_findings.append(findings)

    # Search for encryption key
    search_for_wcdb_key()

    # Summarize
    summarize_findings(all_findings)

    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == "__main__":
    main()
