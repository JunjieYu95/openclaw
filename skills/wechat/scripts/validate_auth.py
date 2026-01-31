#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "itchat>=1.3.10",
#     "pillow>=10.0.0",
# ]
# ///
"""
WeChat Authentication Validation Script

This script validates the WeChat Web authentication workflow and tests
what data we can access. Run this first to confirm the approach works
before building the full skill.

Usage:
    uv run validate_auth.py [--force-login] [--test-all]

Steps:
    1. Displays QR code in terminal
    2. Scan with WeChat mobile app
    3. Tests various data access capabilities
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Session storage location
SESSION_DIR = Path.home() / ".openclaw" / "wechat"
SESSION_FILE = SESSION_DIR / "itchat.pkl"


def setup_session_dir():
    """Create session directory if it doesn't exist."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Session directory: {SESSION_DIR}")


def login(force: bool = False) -> bool:
    """
    Authenticate with WeChat via QR code.

    Args:
        force: If True, force new login even if session exists

    Returns:
        True if login successful, False otherwise
    """
    import itchat

    setup_session_dir()

    print("\n" + "=" * 50)
    print("WeChat Authentication")
    print("=" * 50)

    if SESSION_FILE.exists() and not force:
        print(f"Found existing session: {SESSION_FILE}")
        print("Attempting to reuse session...")
        try:
            itchat.auto_login(
                hotReload=True,
                statusStorageDir=str(SESSION_FILE),
                enableCmdQR=False  # Don't show QR if reusing session
            )
            print("Session restored successfully!")
            return True
        except Exception as e:
            print(f"Session restore failed: {e}")
            print("Will attempt fresh login...")

    print("\nStarting fresh login...")
    print("A QR code will appear below. Scan it with your WeChat mobile app.")
    print("(Open WeChat -> '+' -> Scan QR Code)\n")

    try:
        # enableCmdQR=2 for better terminal QR display
        # Use negative number for light terminals: enableCmdQR=-2
        itchat.auto_login(
            hotReload=True,
            statusStorageDir=str(SESSION_FILE),
            enableCmdQR=2,  # Set to -2 if your terminal has light background
            qrCallback=None  # Use default QR display
        )
        print("\nLogin successful!")
        return True
    except Exception as e:
        print(f"\nLogin failed: {e}")
        return False


def test_basic_info():
    """Test if we can get basic account info."""
    import itchat

    print("\n" + "-" * 50)
    print("Test 1: Basic Account Info")
    print("-" * 50)

    try:
        # Get self info
        self_info = itchat.search_friends()
        if self_info:
            print(f"Logged in as: {self_info.get('NickName', 'Unknown')}")
            print(f"WeChat ID: {self_info.get('UserName', 'Unknown')[:20]}...")
            return True
        else:
            print("Could not retrieve account info")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_contacts():
    """Test if we can access contacts."""
    import itchat

    print("\n" + "-" * 50)
    print("Test 2: Contacts Access")
    print("-" * 50)

    try:
        # Get friends list
        friends = itchat.get_friends(update=True)
        print(f"Total contacts found: {len(friends)}")

        if friends:
            # Show first 5 contacts (anonymized)
            print("\nSample contacts (first 5):")
            for i, friend in enumerate(friends[:5]):
                nickname = friend.get('NickName', 'Unknown')
                remark = friend.get('RemarkName', '')
                display = remark if remark else nickname
                print(f"  {i+1}. {display}")
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chatrooms():
    """Test if we can access group chats."""
    import itchat

    print("\n" + "-" * 50)
    print("Test 3: Group Chats Access")
    print("-" * 50)

    try:
        chatrooms = itchat.get_chatrooms(update=True)
        print(f"Total groups found: {len(chatrooms)}")

        if chatrooms:
            print("\nSample groups (first 5):")
            for i, room in enumerate(chatrooms[:5]):
                name = room.get('NickName', 'Unnamed Group')
                member_count = room.get('MemberCount', '?')
                print(f"  {i+1}. {name} ({member_count} members)")
            return True
        return len(chatrooms) >= 0  # Success even if no groups
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_messages():
    """Test if we can receive messages (brief test)."""
    import itchat

    print("\n" + "-" * 50)
    print("Test 4: Message Reception Capability")
    print("-" * 50)

    try:
        # We can't easily test message history without actually receiving messages
        # But we can check if the message handler registration works

        @itchat.msg_register(itchat.content.TEXT)
        def text_handler(msg):
            pass

        print("Message handler registration: OK")
        print("(Full message history requires active message reception)")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_moments():
    """
    Test Moments (朋友圈) access.

    NOTE: itchat does NOT have native Moments support.
    The WeChat Web API does not expose Moments data.
    This test documents this limitation.
    """
    print("\n" + "-" * 50)
    print("Test 5: Moments (朋友圈) Access")
    print("-" * 50)

    print("""
IMPORTANT FINDING:
The WeChat Web API (used by itchat) does NOT support Moments access.

Moments (朋友圈) is only accessible through:
1. WeChat Mobile App (no API)
2. WeChat PC/Mac App (no official API)
3. Third-party tools using reverse-engineering (risky, may violate TOS)

Alternative approaches to consider:
- Manual export from WeChat and parse the data
- Use WeChat Official Account API (for public accounts only)
- Use WeChat Work API (for enterprise accounts)
- Mobile automation tools (Appium) - complex setup

Recommendation:
Focus on features that ARE accessible via Web API:
- Contacts management
- Message sending/receiving
- Group chat access
- File transfers
""")

    return False  # Moments not accessible


def test_sns_timeline():
    """
    Attempt to access SNS (Social Networking Service) which includes Moments.
    This is an experimental test.
    """
    import itchat

    print("\n" + "-" * 50)
    print("Test 6: SNS/Timeline Experimental Access")
    print("-" * 50)

    try:
        # Check if there are any SNS-related methods
        sns_methods = [m for m in dir(itchat) if 'sns' in m.lower() or 'timeline' in m.lower()]

        if sns_methods:
            print(f"Found SNS-related methods: {sns_methods}")
        else:
            print("No SNS/Timeline methods found in itchat")

        # Try to access through the core module
        if hasattr(itchat, 'Core'):
            core = itchat.Core()
            core_methods = [m for m in dir(core) if 'sns' in m.lower() or 'moment' in m.lower()]
            if core_methods:
                print(f"Core SNS methods: {core_methods}")

        print("\nConclusion: Standard itchat does not expose Moments API")
        return False
    except Exception as e:
        print(f"Error during exploration: {e}")
        return False


def generate_report(results: dict):
    """Generate a summary report of all tests."""
    print("\n" + "=" * 50)
    print("VALIDATION REPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Session file: {SESSION_FILE}")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "[OK]" if passed else "[X]"
        print(f"  {icon} {test_name}: {status}")

    print("\n" + "-" * 50)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"Results: {passed}/{total} tests passed")

    # Recommendations
    print("\n" + "=" * 50)
    print("RECOMMENDATIONS")
    print("=" * 50)

    if results.get('basic_info') and results.get('contacts'):
        print("""
The WeChat Web API connection works! However, Moments access is NOT
available through this API.

For the WeChat skill, we can implement:
1. Contact listing and search
2. Message sending and receiving
3. Group chat management
4. File sharing

For Moments specifically, alternative approaches needed:
- Consider using WeChatFerry (https://github.com/lich0821/WeChatFerry)
  which hooks into the Windows WeChat client
- Or use Appium for mobile automation
- Or accept manual data export workflow
""")
    else:
        print("""
Authentication may have issues. Please check:
1. Is WeChat Web enabled for your account?
2. Some accounts (especially new ones) may have Web access restricted
3. Try logging in at https://web.wechat.com first to verify access
""")


def main():
    parser = argparse.ArgumentParser(
        description="Validate WeChat authentication and data access"
    )
    parser.add_argument(
        "--force-login", "-f",
        action="store_true",
        help="Force new login even if session exists"
    )
    parser.add_argument(
        "--test-all", "-a",
        action="store_true",
        help="Run all tests including experimental ones"
    )
    parser.add_argument(
        "--light-terminal",
        action="store_true",
        help="Use QR code colors for light terminal background"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChat Access Validation Script")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Attempt login
    if not login(force=args.force_login):
        print("\nLogin failed. Cannot proceed with tests.")
        sys.exit(1)

    # Run tests
    results = {}

    results['basic_info'] = test_basic_info()
    results['contacts'] = test_contacts()
    results['chatrooms'] = test_chatrooms()
    results['messages'] = test_messages()
    results['moments'] = test_moments()

    if args.test_all:
        results['sns_experimental'] = test_sns_timeline()

    # Generate report
    generate_report(results)

    # Logout option
    print("\nNote: Session is preserved for future use.")
    print(f"To clear session: rm {SESSION_FILE}")


if __name__ == "__main__":
    main()
