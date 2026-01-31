#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pywxdump>=2.1.0",
# ]
# ///
"""
WeChat macOS Local Database Validation Script

This script checks if we can access WeChat data from the local Mac database.
WeChat for Mac stores messages, contacts, and cached Moments locally.

REQUIREMENTS:
1. macOS with WeChat Desktop installed
2. WeChat must have been used (to create local database)
3. May need to grant Terminal/Python disk access in System Preferences

Usage:
    uv run validate_mac.py [--find-db] [--test-decrypt]

For more info: https://github.com/xaoyaoo/PyWxDump
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import platform


def check_platform():
    """Verify we're on macOS."""
    print("\n" + "=" * 50)
    print("Platform Check")
    print("=" * 50)

    if platform.system() != "Darwin":
        print(f"Current platform: {platform.system()}")
        print("This script is for macOS only.")
        return False

    print(f"Platform: macOS {platform.mac_ver()[0]}")
    print("Status: SUPPORTED")
    return True


def find_wechat_data_dir():
    """Find WeChat data directory on macOS."""
    print("\n" + "-" * 50)
    print("Locating WeChat Data Directory")
    print("-" * 50)

    # Common WeChat data locations on macOS
    home = Path.home()
    possible_paths = [
        home / "Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat",
        home / "Library/Containers/com.tencent.xinWeChat/Data",
        home / "Library/Application Support/com.tencent.xinWeChat",
    ]

    found_paths = []
    for path in possible_paths:
        if path.exists():
            found_paths.append(path)
            print(f"Found: {path}")

    if not found_paths:
        print("WeChat data directory NOT FOUND")
        print("\nPossible reasons:")
        print("1. WeChat for Mac not installed")
        print("2. WeChat never logged in on this Mac")
        print("3. Data stored in non-standard location")
        return None

    # Use the first found path
    return found_paths[0]


def find_wechat_databases(data_dir: Path):
    """Find WeChat SQLite databases."""
    print("\n" + "-" * 50)
    print("Searching for WeChat Databases")
    print("-" * 50)

    if not data_dir:
        print("No data directory provided")
        return []

    # Search for database files
    db_files = []

    # Look for common database patterns
    patterns = ["*.db", "*.sqlite", "*MSG*.db", "*Contact*.db", "*WCDB*"]

    for pattern in patterns:
        found = list(data_dir.rglob(pattern))
        db_files.extend(found)

    # Deduplicate
    db_files = list(set(db_files))

    if db_files:
        print(f"Found {len(db_files)} database file(s):")
        for db in db_files[:10]:  # Show first 10
            size = db.stat().st_size / 1024  # KB
            print(f"  - {db.name} ({size:.1f} KB)")
        if len(db_files) > 10:
            print(f"  ... and {len(db_files) - 10} more")
    else:
        print("No database files found")
        print("WeChat may use encrypted storage on macOS")

    return db_files


def check_encryption_status(data_dir: Path):
    """Check if WeChat data is encrypted."""
    print("\n" + "-" * 50)
    print("Encryption Status Check")
    print("-" * 50)

    # Look for encryption-related files
    key_indicators = [
        "EnMicroMsg.db",  # Encrypted message DB (Android pattern)
        "WCDB",  # WeChat's custom encrypted DB format
    ]

    encrypted = False
    for indicator in key_indicators:
        found = list(data_dir.rglob(f"*{indicator}*"))
        if found:
            print(f"Found encrypted database indicator: {indicator}")
            encrypted = True

    if encrypted:
        print("\nWeChat data appears to be ENCRYPTED")
        print("Decryption key extraction may be required")
    else:
        print("\nEncryption status: UNKNOWN")
        print("May need further investigation")

    return encrypted


def test_pywxdump():
    """Test PyWxDump functionality."""
    print("\n" + "-" * 50)
    print("PyWxDump Module Test")
    print("-" * 50)

    try:
        import pywxdump
        print(f"PyWxDump version: {pywxdump.__version__ if hasattr(pywxdump, '__version__') else 'unknown'}")

        # List available functions
        functions = [f for f in dir(pywxdump) if not f.startswith('_')]
        print(f"Available modules: {functions[:10]}...")

        # Check for key functions
        key_functions = ['get_wechat_db', 'decrypt', 'read_info', 'BiasAddr', 'get_key']
        available = [f for f in key_functions if hasattr(pywxdump, f) or f in functions]
        print(f"Key functions available: {available}")

        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def try_get_wechat_info():
    """Try to get WeChat account info using PyWxDump."""
    print("\n" + "-" * 50)
    print("WeChat Info Extraction Attempt")
    print("-" * 50)

    try:
        from pywxdump import get_wechat_db, BiasAddr

        # Try to find WeChat process and extract info
        print("Attempting to locate WeChat process...")

        # This typically works better on Windows
        # On macOS, we may need different approach
        try:
            result = get_wechat_db()
            if result:
                print(f"WeChat info found: {result}")
                return True
        except Exception as e:
            print(f"get_wechat_db failed: {e}")

        # Try BiasAddr for key extraction
        try:
            bias = BiasAddr()
            print(f"BiasAddr initialized")
        except Exception as e:
            print(f"BiasAddr failed: {e}")

        print("\nNote: PyWxDump's automatic extraction works best on Windows.")
        print("For macOS, manual database location may be needed.")
        return False

    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_wechat_running():
    """Check if WeChat is running on macOS."""
    print("\n" + "-" * 50)
    print("WeChat Process Check")
    print("-" * 50)

    try:
        result = subprocess.run(
            ["pgrep", "-x", "WeChat"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pid = result.stdout.strip()
            print(f"WeChat is RUNNING (PID: {pid})")
            return True
        else:
            print("WeChat is NOT RUNNING")
            print("Some extraction methods require WeChat to be running")
            return False
    except Exception as e:
        print(f"Could not check: {e}")
        return False


def explore_alternative_approaches():
    """Document alternative approaches for macOS."""
    print("\n" + "=" * 50)
    print("ALTERNATIVE APPROACHES FOR macOS")
    print("=" * 50)

    print("""
Since WeChat Web is blocked and desktop extraction is complex on macOS,
here are alternative approaches:

1. **Manual Chat Export**
   - WeChat Mac → Settings → General → Export Chat History
   - Skill parses the exported HTML/text files
   - Pros: Simple, reliable
   - Cons: Manual step required, no Moments

2. **iPhone Backup Parsing**
   - Create unencrypted iPhone backup via Finder
   - Parse WeChat data from backup
   - Pros: Access to more data including Moments cache
   - Cons: Requires iPhone, backup process

3. **Appium Mobile Automation**
   - Automate WeChat on iPhone via Appium
   - Pros: Full access including Moments
   - Cons: Complex setup, requires iPhone connected

4. **WeChat Work (企业微信)**
   - If you have WeChat Work account
   - Has official API with proper access
   - Pros: Official, stable API
   - Cons: Requires enterprise account

5. **Keyboard Maestro / AppleScript**
   - Automate WeChat Mac UI
   - Pros: Works with current app
   - Cons: Fragile, limited data access, no Moments

RECOMMENDATION FOR YOUR USE CASE:
---------------------------------
For Moments summarization on macOS, the most practical options are:

A) **iPhone Backup Method** - Best for one-time/periodic access
   - Back up iPhone → Extract Moments from backup → Summarize

B) **Manual Screenshot + OCR** - Quick and dirty
   - Screenshot Moments → Use vision model to extract text → Summarize

C) **WeChat Work API** - If you have enterprise access
   - Clean API access, but limited to work account data
""")


def generate_report(results: dict):
    """Generate summary report."""
    print("\n" + "=" * 50)
    print("macOS VALIDATION REPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL/PARTIAL"
        icon = "[OK]" if passed else "[--]"
        print(f"  {icon} {test_name}: {status}")

    print("\n" + "-" * 50)
    print("SUMMARY")
    print("-" * 50)

    if results.get('data_dir_found'):
        print("WeChat data directory exists on this Mac.")
        print("However, direct database access on macOS is limited.")

    print("\nFor Moments access on macOS, recommend:")
    print("1. iPhone backup parsing (if you have iPhone)")
    print("2. Manual export + parsing workflow")
    print("3. Screenshot + OCR approach for quick summaries")


def main():
    parser = argparse.ArgumentParser(
        description="Validate WeChat data access on macOS"
    )
    parser.add_argument(
        "--find-db",
        action="store_true",
        help="Search for WeChat database files"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show more details"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChat macOS Validation Script")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Platform check
    results['platform'] = check_platform()
    if not results['platform']:
        sys.exit(1)

    # Check if WeChat is running
    results['wechat_running'] = check_wechat_running()

    # Find data directory
    data_dir = find_wechat_data_dir()
    results['data_dir_found'] = data_dir is not None

    if data_dir and args.find_db:
        db_files = find_wechat_databases(data_dir)
        results['databases_found'] = len(db_files) > 0

        if db_files:
            check_encryption_status(data_dir)

    # Test PyWxDump
    results['pywxdump_available'] = test_pywxdump()

    # Try extraction (usually fails on macOS but worth trying)
    results['auto_extraction'] = try_get_wechat_info()

    # Show alternatives
    explore_alternative_approaches()

    # Generate report
    generate_report(results)


if __name__ == "__main__":
    main()
