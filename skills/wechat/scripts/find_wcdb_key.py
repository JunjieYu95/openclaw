#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
WeChat Encryption Key Finder

WeChat uses WCDB (SQLCipher-based) encryption.
The key is typically stored in macOS Keychain or derived from account info.

This script helps locate and extract the encryption key.

Usage:
    uv run find_wcdb_key.py
"""

import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path


WECHAT_CONTAINER = Path.home() / "Library/Containers/com.tencent.xinWeChat/Data"


def search_keychain_entries():
    """Search Keychain for WeChat-related entries."""
    print("=" * 60)
    print("Searching Keychain for WeChat Entries")
    print("=" * 60)

    # Search terms
    search_terms = [
        "com.tencent.xinWeChat",
        "WeChat",
        "wechat",
        "WCDB",
        "xinWeChat",
    ]

    found_entries = []

    for term in search_terms:
        print(f"\nSearching for: {term}")
        try:
            # Use security command to find generic passwords
            result = subprocess.run(
                ["security", "find-generic-password", "-s", term, "-g"],
                capture_output=True,
                text=True
            )

            if "password:" in result.stderr or "password:" in result.stdout:
                print(f"  [FOUND] Entry with service: {term}")
                found_entries.append({
                    "service": term,
                    "output": result.stderr + result.stdout
                })
            else:
                # Try account-based search
                result = subprocess.run(
                    ["security", "find-generic-password", "-a", term, "-g"],
                    capture_output=True,
                    text=True
                )
                if "password:" in result.stderr:
                    print(f"  [FOUND] Entry with account: {term}")
                    found_entries.append({
                        "account": term,
                        "output": result.stderr
                    })

        except Exception as e:
            print(f"  Error: {e}")

    # Also try to list all and filter
    print("\nListing all keychain items and filtering...")
    try:
        result = subprocess.run(
            ["security", "dump-keychain"],
            capture_output=True,
            text=True,
            timeout=60
        )

        lines = result.stdout.split('\n')
        in_wechat_entry = False
        current_entry = []

        for line in lines:
            if 'keychain:' in line.lower():
                if current_entry and in_wechat_entry:
                    found_entries.append({"dump_entry": '\n'.join(current_entry)})
                current_entry = [line]
                in_wechat_entry = False
            else:
                current_entry.append(line)
                if any(term.lower() in line.lower() for term in ['wechat', 'tencent', 'wcdb']):
                    in_wechat_entry = True

        # Print found WeChat-related entries
        wechat_lines = [l for l in lines if any(t.lower() in l.lower() for t in ['wechat', 'tencent'])]
        if wechat_lines:
            print(f"\nFound {len(wechat_lines)} WeChat-related lines in keychain:")
            for line in wechat_lines[:20]:
                print(f"  {line.strip()}")

    except subprocess.TimeoutExpired:
        print("  Keychain dump timed out")
    except Exception as e:
        print(f"  Error: {e}")

    return found_entries


def find_key_in_plist():
    """Look for encryption key in plist files."""
    print("\n" + "=" * 60)
    print("Searching Plist Files for Keys")
    print("=" * 60)

    if not WECHAT_CONTAINER.exists():
        print("WeChat container not found")
        return None

    key_patterns = [
        r'[A-Fa-f0-9]{64}',  # 256-bit hex key
        r'[A-Fa-f0-9]{32}',  # 128-bit hex key
    ]

    found_keys = []

    for plist_path in WECHAT_CONTAINER.rglob("*.plist"):
        try:
            with open(plist_path, 'rb') as f:
                try:
                    data = plistlib.load(f)
                except:
                    continue

            # Convert to string and search for key patterns
            data_str = str(data)

            for pattern in key_patterns:
                matches = re.findall(pattern, data_str)
                for match in matches:
                    if len(match) >= 32:  # At least 128-bit
                        # Verify it's not a common hash (like file paths)
                        if match not in found_keys:
                            found_keys.append(match)
                            print(f"\nPotential key in {plist_path.name}:")
                            print(f"  {match[:32]}... (length: {len(match)})")

        except Exception as e:
            continue

    return found_keys


def find_key_files():
    """Look for dedicated key files."""
    print("\n" + "=" * 60)
    print("Searching for Key Files")
    print("=" * 60)

    if not WECHAT_CONTAINER.exists():
        print("WeChat container not found")
        return

    key_file_patterns = ["*key*", "*Key*", "*KEY*", "*.key", "*secret*", "*cipher*"]

    for pattern in key_file_patterns:
        for keyfile in WECHAT_CONTAINER.rglob(pattern):
            if keyfile.is_file() and keyfile.stat().st_size < 10000:  # Small files only
                print(f"\n[KEY FILE] {keyfile}")
                print(f"  Size: {keyfile.stat().st_size} bytes")

                # Try to read content
                try:
                    with open(keyfile, 'rb') as f:
                        content = f.read()

                    # Check if it's text
                    try:
                        text = content.decode('utf-8').strip()
                        if len(text) < 200:
                            print(f"  Content: {text[:100]}")
                    except:
                        # Binary - show hex
                        print(f"  Hex: {content[:32].hex()}")

                except Exception as e:
                    print(f"  Could not read: {e}")


def check_user_defaults():
    """Check UserDefaults for WeChat settings."""
    print("\n" + "=" * 60)
    print("Checking UserDefaults")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["defaults", "read", "com.tencent.xinWeChat"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output = result.stdout
            print("WeChat UserDefaults found:")

            # Look for key-like values
            for line in output.split('\n'):
                if any(term in line.lower() for term in ['key', 'secret', 'token', 'cipher', 'crypt']):
                    print(f"  {line.strip()}")

            # Look for hex strings that might be keys
            hex_matches = re.findall(r'[A-Fa-f0-9]{32,64}', output)
            if hex_matches:
                print("\nPotential keys in UserDefaults:")
                for match in set(hex_matches):
                    print(f"  {match}")

        else:
            print("No UserDefaults found for WeChat")

    except Exception as e:
        print(f"Error: {e}")


def find_account_info():
    """Find WeChat account information that might help derive the key."""
    print("\n" + "=" * 60)
    print("Finding Account Information")
    print("=" * 60)

    # Look for account identifiers
    account_indicators = []

    # Check for wxid in file/folder names
    for base in [WECHAT_CONTAINER, Path.home() / "Library/Group Containers/group.com.tencent.xinWeChat"]:
        if not base.exists():
            continue

        for item in base.rglob("*"):
            name = item.name.lower()
            if name.startswith("wxid_") or "wxid" in name:
                print(f"[WXID] {item}")
                account_indicators.append(item.name)

            # Look for MD5-like folder names (32 hex chars)
            if len(item.name) == 32 and all(c in '0123456789abcdef' for c in item.name.lower()):
                if item.is_dir():
                    print(f"[ACCOUNT DIR] {item}")
                    account_indicators.append(item.name)

    return account_indicators


def try_known_key_derivation():
    """
    Try known WCDB key derivation methods.

    WCDB typically derives keys from:
    - Device UDID + User ID (wxid)
    - Or stores encrypted key in Keychain

    This is informational - actual derivation would need more research.
    """
    print("\n" + "=" * 60)
    print("Key Derivation Information")
    print("=" * 60)

    print("""
WCDB Encryption Key Derivation:
───────────────────────────────

WeChat for Mac uses WCDB (based on SQLCipher) with keys typically:

1. DERIVED FROM:
   - Device identifier (UDID or serial number)
   - User account ID (wxid_xxxxx)
   - Combined with app-specific salt

2. STORED IN:
   - macOS Keychain (most common)
   - Encrypted preference file
   - Derived at runtime from system info

MANUAL KEY EXTRACTION:
──────────────────────

Option A: Keychain Access (GUI)
1. Open "Keychain Access" app
2. Search for "WeChat" or "tencent"
3. Double-click entries → Show Password
4. Authenticate with your Mac password

Option B: Security Command
Run these commands to find and show passwords:

  # Find all WeChat keychain entries
  security find-generic-password -s "com.tencent.xinWeChat"

  # If found, get password (will prompt for auth)
  security find-generic-password -s "com.tencent.xinWeChat" -w

Option C: LLDB (requires Xcode, SIP disabled)
1. Attach to running WeChat: lldb -p $(pgrep WeChat)
2. Set breakpoint on SQLCipher key function
3. Print key when breakpoint hits

ONCE YOU HAVE THE KEY:
──────────────────────
We can decrypt the WCDB databases with:
  - sqlcipher CLI tool
  - Python's pysqlcipher3 library
  - Or custom WCDB decryption script
""")


def show_next_steps():
    """Show recommended next steps."""
    print("\n" + "=" * 60)
    print("RECOMMENDED NEXT STEPS")
    print("=" * 60)

    print("""
1. MANUAL KEYCHAIN CHECK (Easiest)
   ─────────────────────────────────
   a) Open "Keychain Access" app (Spotlight → "Keychain Access")
   b) In search box, type: WeChat
   c) Look for entries like:
      - com.tencent.xinWeChat
      - WeChat (key)
      - WCDB key
   d) Double-click → Check "Show password"
   e) Enter your Mac password when prompted

   If you find a 64-character hex string, that's likely the key!

2. IF KEY FOUND
   ─────────────────────────────────
   Share the key length and first/last 4 characters (for verification).
   I'll create a decryption script to read your WeChat data.

   Example: "Found key: 64 chars, starts with 'a1b2', ends with 'c3d4'"

3. IF NO KEY IN KEYCHAIN
   ─────────────────────────────────
   The key might be derived at runtime. Options:
   a) Use memory extraction (complex)
   b) Try Windows VM with WeChatFerry
   c) Use WeChat's official export (if available)

4. ALTERNATIVE: CHECK FOR EXPORT FEATURE
   ─────────────────────────────────
   Open WeChat → Preferences → General
   Look for any "Export" or "Backup" options
""")


def main():
    print("=" * 60)
    print("WeChat WCDB Key Finder")
    print("=" * 60)
    print("Looking for encryption key to access WeChat databases...\n")

    # Search various locations
    keychain_entries = search_keychain_entries()
    plist_keys = find_key_in_plist()
    find_key_files()
    check_user_defaults()
    account_info = find_account_info()

    # Show derivation info
    try_known_key_derivation()

    # Show next steps
    show_next_steps()


if __name__ == "__main__":
    main()
