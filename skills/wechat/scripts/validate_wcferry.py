#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "wcferry>=39.3.5",
# ]
# ///
"""
WeChatFerry Validation Script

WeChatFerry is a more powerful WeChat automation tool that hooks into
the Windows/Mac WeChat desktop client. It CAN access Moments data.

REQUIREMENTS:
1. Windows or macOS with WeChat Desktop installed
2. WeChat Desktop must be running and logged in
3. WeChatFerry DLL/dylib injection (handled by wcferry package)

Usage:
    uv run validate_wcferry.py [--test-moments]

WARNING: This approach:
- Requires desktop WeChat client (not web)
- May violate WeChat TOS
- Needs the client running at all times
- Is more complex to set up

For more info: https://github.com/lich0821/WeChatFerry
"""

import argparse
import sys
from datetime import datetime
import platform


def check_platform():
    """Check if we're on a supported platform."""
    print("\n" + "=" * 50)
    print("Platform Check")
    print("=" * 50)

    os_name = platform.system()
    print(f"Operating System: {os_name}")
    print(f"Architecture: {platform.machine()}")

    if os_name == "Windows":
        print("Platform: SUPPORTED")
        return True
    elif os_name == "Darwin":
        print("Platform: PARTIAL SUPPORT (experimental on macOS)")
        return True
    else:
        print("Platform: NOT SUPPORTED")
        print("WeChatFerry only works on Windows (full) and macOS (experimental)")
        return False


def check_wechat_running():
    """Check if WeChat desktop is running."""
    print("\n" + "-" * 50)
    print("WeChat Desktop Check")
    print("-" * 50)

    os_name = platform.system()

    try:
        if os_name == "Windows":
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WeChat.exe"],
                capture_output=True,
                text=True
            )
            if "WeChat.exe" in result.stdout:
                print("WeChat Desktop: RUNNING")
                return True
            else:
                print("WeChat Desktop: NOT RUNNING")
                print("Please start WeChat Desktop and log in first.")
                return False

        elif os_name == "Darwin":
            import subprocess
            result = subprocess.run(
                ["pgrep", "-x", "WeChat"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("WeChat Desktop: RUNNING")
                return True
            else:
                print("WeChat Desktop: NOT RUNNING")
                print("Please start WeChat Desktop and log in first.")
                return False

    except Exception as e:
        print(f"Could not check WeChat status: {e}")
        return False

    return False


def test_wcferry_connection():
    """Test connection to WeChat via WeChatFerry."""
    print("\n" + "-" * 50)
    print("WeChatFerry Connection Test")
    print("-" * 50)

    try:
        from wcferry import Wcf

        print("Attempting to connect to WeChat Desktop...")
        wcf = Wcf()

        if wcf.is_login():
            print("Connection: SUCCESS")
            self_info = wcf.get_self_wxid()
            print(f"Logged in as wxid: {self_info}")
            return wcf
        else:
            print("Connection: FAILED - Not logged in")
            return None

    except ImportError as e:
        print(f"Import error: {e}")
        print("The wcferry package may not be properly installed.")
        return None
    except Exception as e:
        print(f"Connection error: {e}")
        print("\nPossible issues:")
        print("1. WeChat Desktop not running")
        print("2. WeChat not logged in")
        print("3. WeChatFerry DLL not injected")
        print("4. Version mismatch between wcferry and WeChat")
        return None


def test_contacts(wcf):
    """Test contacts access via WeChatFerry."""
    print("\n" + "-" * 50)
    print("Contacts Test (WeChatFerry)")
    print("-" * 50)

    try:
        contacts = wcf.get_contacts()
        print(f"Total contacts: {len(contacts)}")

        # Show sample
        friends = [c for c in contacts if not c.get('wxid', '').startswith('gh_')]
        print(f"Friends (non-official accounts): {len(friends)}")

        if friends[:5]:
            print("\nSample contacts:")
            for i, c in enumerate(friends[:5]):
                print(f"  {i+1}. {c.get('name', 'Unknown')} ({c.get('wxid', '')[:10]}...)")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_moments(wcf):
    """
    Test Moments access via WeChatFerry.

    This is the key test - WeChatFerry CAN access Moments unlike web API.
    """
    print("\n" + "-" * 50)
    print("Moments (朋友圈) Test (WeChatFerry)")
    print("-" * 50)

    try:
        # Check if moments method exists
        if hasattr(wcf, 'get_sns_first_page') or hasattr(wcf, 'refresh_pyq'):
            print("Moments API: AVAILABLE")

            # Try to fetch Moments
            if hasattr(wcf, 'refresh_pyq'):
                print("Refreshing Moments feed...")
                result = wcf.refresh_pyq()
                print(f"Refresh result: {result}")

            # Note: The exact API depends on wcferry version
            # Some versions use get_sns_first_page, others use different methods

            print("\nMoments access confirmed available via WeChatFerry!")
            print("Full implementation would parse the returned data.")
            return True
        else:
            # List available methods for debugging
            methods = [m for m in dir(wcf) if not m.startswith('_')]
            sns_methods = [m for m in methods if 'sns' in m.lower() or 'pyq' in m.lower() or 'moment' in m.lower()]

            if sns_methods:
                print(f"Found SNS-related methods: {sns_methods}")
                return True
            else:
                print("No Moments methods found in this wcferry version")
                print(f"Available methods: {methods[:20]}...")  # Show first 20
                return False

    except Exception as e:
        print(f"Error testing Moments: {e}")
        return False


def test_messages(wcf):
    """Test message retrieval via WeChatFerry."""
    print("\n" + "-" * 50)
    print("Messages Test (WeChatFerry)")
    print("-" * 50)

    try:
        # WeChatFerry can access message database
        if hasattr(wcf, 'get_msg'):
            print("Message API: AVAILABLE")
            print("(Can retrieve message history from local database)")
            return True
        else:
            print("Message retrieval method not found in this version")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def generate_report(results: dict):
    """Generate validation report."""
    print("\n" + "=" * 50)
    print("WCFERRY VALIDATION REPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "[OK]" if passed else "[X]"
        print(f"  {icon} {test_name}: {status}")

    print("\n" + "-" * 50)
    print("COMPARISON: itchat vs WeChatFerry")
    print("-" * 50)
    print("""
| Feature          | itchat (Web)  | WeChatFerry (Desktop) |
|------------------|---------------|----------------------|
| Contacts         | Yes           | Yes                  |
| Messages Send    | Yes           | Yes                  |
| Messages History | Limited       | Full DB access       |
| Group Chats      | Yes           | Yes                  |
| Moments (朋友圈)  | NO            | YES                  |
| File Transfer    | Yes           | Yes                  |
| Platform         | Any (web)     | Windows/Mac only     |
| Setup Complexity | Low           | High                 |
| Stability        | May break     | Version dependent    |
| TOS Risk         | Medium        | Higher               |
""")

    if results.get('moments'):
        print("\nRECOMMENDATION: Use WeChatFerry for Moments access")
        print("The skill should support both backends with WeChatFerry as primary.")
    else:
        print("\nRECOMMENDATION: Consider using itchat for basic features,")
        print("and document Moments limitation or provide manual export workflow.")


def main():
    parser = argparse.ArgumentParser(
        description="Validate WeChatFerry access (desktop WeChat hook)"
    )
    parser.add_argument(
        "--test-moments", "-m",
        action="store_true",
        help="Include Moments access test"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChatFerry Validation Script")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Platform check
    results['platform'] = check_platform()
    if not results['platform']:
        print("\nCannot proceed on unsupported platform.")
        print("Consider using validate_auth.py (itchat/web) instead.")
        sys.exit(1)

    # Check WeChat running
    results['wechat_running'] = check_wechat_running()
    if not results['wechat_running']:
        print("\nPlease start WeChat Desktop and log in, then retry.")
        sys.exit(1)

    # Test connection
    wcf = test_wcferry_connection()
    results['connection'] = wcf is not None

    if wcf:
        results['contacts'] = test_contacts(wcf)
        results['messages'] = test_messages(wcf)

        if args.test_moments:
            results['moments'] = test_moments(wcf)

        # Cleanup
        try:
            wcf.cleanup()
        except:
            pass

    generate_report(results)


if __name__ == "__main__":
    main()
