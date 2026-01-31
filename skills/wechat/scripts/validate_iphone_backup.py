#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "biplist>=1.0.3",
# ]
# ///
"""
WeChat iPhone Backup Validation Script

This script checks if we can extract WeChat data from an iPhone backup.
This is the most reliable way to access WeChat data (including Moments)
on macOS.

REQUIREMENTS:
1. iPhone with WeChat installed
2. Create an UNENCRYPTED backup via Finder (not iCloud)
3. Backup location: ~/Library/Application Support/MobileSync/Backup/

STEPS TO CREATE BACKUP:
1. Connect iPhone to Mac via USB
2. Open Finder, select your iPhone
3. Under "Backups", select "Back up all data on your iPhone to this Mac"
4. UNCHECK "Encrypt local backup" (important!)
5. Click "Back Up Now"

Usage:
    uv run validate_iphone_backup.py [--list-backups] [--check-wechat]
"""

import argparse
import hashlib
import os
import plistlib
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# WeChat app bundle IDs
WECHAT_BUNDLE_IDS = [
    "com.tencent.xin",  # WeChat
    "com.tencent.ww",   # WeChat Work
]

# WeChat domain identifiers in backup manifest
WECHAT_DOMAINS = [
    "AppDomain-com.tencent.xin",
    "AppDomainGroup-group.com.tencent.xin",
]


def get_backup_directory():
    """Get the iOS backup directory path."""
    return Path.home() / "Library/Application Support/MobileSync/Backup"


def list_backups():
    """List all iOS backups found on this Mac."""
    print("\n" + "=" * 50)
    print("iOS Backups on This Mac")
    print("=" * 50)

    backup_dir = get_backup_directory()

    if not backup_dir.exists():
        print(f"Backup directory not found: {backup_dir}")
        print("No iOS backups exist on this Mac.")
        return []

    backups = []

    for item in backup_dir.iterdir():
        if item.is_dir():
            info_plist = item / "Info.plist"
            if info_plist.exists():
                try:
                    with open(info_plist, 'rb') as f:
                        info = plistlib.load(f)

                    backup_info = {
                        'path': item,
                        'device_name': info.get('Device Name', 'Unknown'),
                        'product_type': info.get('Product Type', 'Unknown'),
                        'ios_version': info.get('Product Version', 'Unknown'),
                        'date': info.get('Last Backup Date', 'Unknown'),
                        'encrypted': info.get('IsEncrypted', False),
                    }
                    backups.append(backup_info)

                    encrypted_status = "ENCRYPTED" if backup_info['encrypted'] else "unencrypted"
                    print(f"\nBackup: {item.name[:20]}...")
                    print(f"  Device: {backup_info['device_name']}")
                    print(f"  iOS: {backup_info['ios_version']}")
                    print(f"  Date: {backup_info['date']}")
                    print(f"  Status: {encrypted_status}")

                    if backup_info['encrypted']:
                        print("  WARNING: Encrypted backups cannot be read without password")

                except Exception as e:
                    print(f"\nBackup: {item.name}")
                    print(f"  Error reading info: {e}")

    if not backups:
        print("No valid iOS backups found.")
        print("\nTo create a backup:")
        print("1. Connect iPhone via USB")
        print("2. Open Finder → Select iPhone")
        print("3. Click 'Back Up Now' (uncheck encryption)")

    return backups


def find_wechat_in_backup(backup_path: Path):
    """Check if WeChat data exists in the backup."""
    print("\n" + "-" * 50)
    print("Checking for WeChat Data in Backup")
    print("-" * 50)

    manifest_db = backup_path / "Manifest.db"
    manifest_plist = backup_path / "Manifest.plist"

    # Check for encrypted backup
    if manifest_plist.exists():
        try:
            with open(manifest_plist, 'rb') as f:
                manifest = plistlib.load(f)
            if manifest.get('IsEncrypted', False):
                print("ERROR: This backup is encrypted.")
                print("Please create an unencrypted backup to proceed.")
                return None
        except:
            pass

    if not manifest_db.exists():
        print(f"Manifest.db not found in backup")
        return None

    try:
        conn = sqlite3.connect(str(manifest_db))
        cursor = conn.cursor()

        # Find WeChat files in backup
        wechat_files = []

        for domain in WECHAT_DOMAINS:
            cursor.execute(
                "SELECT fileID, domain, relativePath FROM Files WHERE domain = ?",
                (domain,)
            )
            files = cursor.fetchall()
            wechat_files.extend(files)

        # Also search by bundle ID pattern
        cursor.execute(
            "SELECT fileID, domain, relativePath FROM Files WHERE domain LIKE '%tencent.xin%'"
        )
        wechat_files.extend(cursor.fetchall())

        conn.close()

        if wechat_files:
            print(f"Found {len(wechat_files)} WeChat-related files in backup")

            # Categorize files
            db_files = [f for f in wechat_files if f[2].endswith('.db') or f[2].endswith('.sqlite')]
            media_files = [f for f in wechat_files if any(ext in f[2].lower() for ext in ['.jpg', '.png', '.mp4', '.gif'])]

            print(f"  - Database files: {len(db_files)}")
            print(f"  - Media files: {len(media_files)}")

            # Show sample database files
            if db_files:
                print("\nSample database files:")
                for file_id, domain, rel_path in db_files[:5]:
                    print(f"  - {rel_path}")

            return {
                'total_files': len(wechat_files),
                'db_files': db_files,
                'media_files': media_files,
            }
        else:
            print("No WeChat data found in this backup")
            print("Make sure WeChat is installed and you've used it on this iPhone")
            return None

    except Exception as e:
        print(f"Error reading backup manifest: {e}")
        return None


def check_moments_data(backup_path: Path, wechat_info: dict):
    """Check for Moments (朋友圈) data in backup."""
    print("\n" + "-" * 50)
    print("Checking for Moments (朋友圈) Data")
    print("-" * 50)

    if not wechat_info or not wechat_info.get('db_files'):
        print("No database files to check")
        return False

    # Moments-related patterns
    moments_patterns = ['sns', 'timeline', 'moment', 'pyq', 'friend']

    moments_dbs = []
    for file_id, domain, rel_path in wechat_info['db_files']:
        path_lower = rel_path.lower()
        if any(pattern in path_lower for pattern in moments_patterns):
            moments_dbs.append((file_id, rel_path))

    if moments_dbs:
        print(f"Found {len(moments_dbs)} potential Moments database(s):")
        for file_id, rel_path in moments_dbs:
            print(f"  - {rel_path}")
            # The actual file in backup is stored by SHA1 hash
            actual_path = backup_path / file_id[:2] / file_id
            if actual_path.exists():
                print(f"    File exists: {actual_path.stat().st_size / 1024:.1f} KB")

        print("\nMoments data appears to be AVAILABLE in backup!")
        return True
    else:
        print("No obvious Moments databases found")
        print("Moments data may be in main message database (WCDB)")
        return False


def try_read_sample_data(backup_path: Path, wechat_info: dict):
    """Try to read some sample WeChat data from backup."""
    print("\n" + "-" * 50)
    print("Attempting to Read Sample Data")
    print("-" * 50)

    if not wechat_info or not wechat_info.get('db_files'):
        print("No database files available")
        return False

    # Try to read a small database
    for file_id, domain, rel_path in wechat_info['db_files'][:5]:
        actual_path = backup_path / file_id[:2] / file_id

        if actual_path.exists() and actual_path.stat().st_size < 10_000_000:  # < 10MB
            try:
                conn = sqlite3.connect(str(actual_path))
                cursor = conn.cursor()

                # List tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                if tables:
                    print(f"\nDatabase: {rel_path}")
                    print(f"Tables found: {[t[0] for t in tables[:10]]}")

                    # Try to get row count from first table
                    if tables:
                        first_table = tables[0][0]
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM [{first_table}]")
                            count = cursor.fetchone()[0]
                            print(f"  {first_table}: {count} rows")
                        except:
                            pass

                conn.close()
                return True

            except sqlite3.DatabaseError as e:
                if "encrypted" in str(e).lower() or "not a database" in str(e).lower():
                    print(f"\nDatabase {rel_path} appears to be encrypted")
                    print("WeChat uses WCDB encryption - decryption key needed")
                continue
            except Exception as e:
                continue

    print("Could not read any databases directly")
    print("WeChat databases are likely encrypted with WCDB")
    return False


def show_recommendations():
    """Show recommendations for proceeding."""
    print("\n" + "=" * 50)
    print("RECOMMENDATIONS")
    print("=" * 50)

    print("""
Based on the validation results, here are your options:

OPTION A: Use iPhone Backup with PyWxDump
-----------------------------------------
PyWxDump has tools to decrypt and parse WeChat backup data.

Steps:
1. Create unencrypted iPhone backup (Finder)
2. Use PyWxDump to extract and decrypt
3. Parse Moments from decrypted databases

Command:
    pip install pywxdump
    pywxdump (follow interactive prompts)


OPTION B: Manual Export + Parse
-------------------------------
If database decryption is too complex:

1. On iPhone, go to WeChat → Me → Settings → General
2. Export chat history (generates HTML/text files)
3. Use skill to parse and summarize exported files

Limitation: No direct Moments export, but chats work well.


OPTION C: Screenshot + Vision Model
-----------------------------------
For quick Moments summaries:

1. Screenshot your Moments feed on iPhone
2. Transfer screenshots to Mac
3. Use vision-capable model to extract and summarize

This is actually quite effective for occasional use!


OPTION D: WeChat for Mac Cache (Limited)
----------------------------------------
WeChat Mac app caches some data locally.
Limited Moments data may be available.

Location: ~/Library/Containers/com.tencent.xinWeChat/


NEXT STEP RECOMMENDATION:
-------------------------
Try PyWxDump's backup extraction tools:

    pip install pywxdump
    python -m pywxdump

This provides the most complete access to WeChat data including Moments.
""")


def generate_report(results: dict):
    """Generate summary report."""
    print("\n" + "=" * 50)
    print("iPHONE BACKUP VALIDATION REPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL/NONE"
        icon = "[OK]" if passed else "[--]"
        print(f"  {icon} {test_name}: {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate WeChat data access via iPhone backup"
    )
    parser.add_argument(
        "--list-backups", "-l",
        action="store_true",
        help="List all iOS backups on this Mac"
    )
    parser.add_argument(
        "--check-wechat", "-w",
        action="store_true",
        help="Check for WeChat data in most recent backup"
    )
    parser.add_argument(
        "--backup-id",
        type=str,
        help="Specific backup ID to check"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChat iPhone Backup Validation")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # List backups
    backups = list_backups()
    results['backups_found'] = len(backups) > 0

    if not backups:
        print("\n" + "-" * 50)
        print("No backups found. Please create an iPhone backup first.")
        show_recommendations()
        return

    # Find unencrypted backup to check
    unencrypted = [b for b in backups if not b['encrypted']]
    results['unencrypted_backup'] = len(unencrypted) > 0

    if not unencrypted:
        print("\n" + "-" * 50)
        print("All backups are ENCRYPTED")
        print("Please create an unencrypted backup:")
        print("  Finder → iPhone → Backups → Uncheck 'Encrypt local backup'")
        show_recommendations()
        generate_report(results)
        return

    # Check most recent unencrypted backup
    backup_to_check = unencrypted[0]
    if args.backup_id:
        matching = [b for b in unencrypted if args.backup_id in str(b['path'])]
        if matching:
            backup_to_check = matching[0]

    print(f"\nUsing backup: {backup_to_check['device_name']}")

    # Check for WeChat data
    wechat_info = find_wechat_in_backup(backup_to_check['path'])
    results['wechat_in_backup'] = wechat_info is not None

    if wechat_info:
        # Check for Moments
        results['moments_data'] = check_moments_data(backup_to_check['path'], wechat_info)

        # Try to read sample
        results['readable_data'] = try_read_sample_data(backup_to_check['path'], wechat_info)

    # Show recommendations
    show_recommendations()

    # Generate report
    generate_report(results)


if __name__ == "__main__":
    main()
