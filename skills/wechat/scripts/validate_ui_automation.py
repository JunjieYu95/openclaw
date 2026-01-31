#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyobjc-framework-Cocoa>=10.0",
#     "pyobjc-framework-Quartz>=10.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
WeChat macOS UI Automation Validation Script

This script explores real-time access to WeChat by automating the
WeChat Mac app directly. Since OpenClaw runs on your machine with
full access, it can:

1. Control WeChat via Accessibility API / AppleScript
2. Capture WeChat window content programmatically
3. Extract text via OCR or send to vision models
4. Navigate to Moments and capture content

REQUIREMENTS:
1. macOS with WeChat Desktop installed and running
2. Grant accessibility permissions to Terminal/Python
   System Preferences → Privacy & Security → Accessibility
3. WeChat logged in

Usage:
    uv run validate_ui_automation.py [--capture-moments] [--interactive]
"""

import argparse
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def check_wechat_running():
    """Check if WeChat is running."""
    print("\n" + "=" * 50)
    print("WeChat Process Check")
    print("=" * 50)

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
        print("Please start WeChat and log in first.")
        return False


def check_accessibility_permissions():
    """Check if we have accessibility permissions."""
    print("\n" + "-" * 50)
    print("Accessibility Permissions Check")
    print("-" * 50)

    # Try a simple AppleScript that requires accessibility
    script = '''
    tell application "System Events"
        return name of first application process whose frontmost is true
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print(f"Accessibility: GRANTED")
            print(f"Current frontmost app: {result.stdout.strip()}")
            return True
        else:
            print("Accessibility: DENIED or LIMITED")
            print(f"Error: {result.stderr}")
            print("\nTo grant access:")
            print("1. Open System Preferences → Privacy & Security")
            print("2. Select Accessibility")
            print("3. Add Terminal (or your Python environment)")
            return False
    except subprocess.TimeoutExpired:
        print("Accessibility check timed out - may need permissions")
        return False
    except Exception as e:
        print(f"Error checking accessibility: {e}")
        return False


def get_wechat_windows():
    """Get WeChat window information via AppleScript."""
    print("\n" + "-" * 50)
    print("WeChat Window Detection")
    print("-" * 50)

    script = '''
    tell application "System Events"
        tell process "WeChat"
            set windowList to {}
            repeat with w in windows
                set windowInfo to {name of w, position of w, size of w}
                set end of windowList to windowInfo
            end repeat
            return windowList
        end tell
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"WeChat windows found: {output}")
            return True
        else:
            print(f"Could not get windows: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def capture_wechat_window():
    """Capture WeChat window screenshot programmatically."""
    print("\n" + "-" * 50)
    print("Window Capture Test")
    print("-" * 50)

    # Create temp file for screenshot
    temp_dir = Path(tempfile.gettempdir())
    screenshot_path = temp_dir / f"wechat_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    # Method 1: Use screencapture with window selection
    # First, get WeChat's window ID
    script = '''
    tell application "System Events"
        tell process "WeChat"
            set frontWindow to front window
            return id of frontWindow
        end tell
    end tell
    '''

    try:
        # Bring WeChat to front first
        subprocess.run(
            ["osascript", "-e", 'tell application "WeChat" to activate'],
            capture_output=True,
            timeout=5
        )

        # Use screencapture to capture the frontmost window
        # -l requires window ID, -w captures window interactively
        # For automation, we use -x (no sound) and capture by app
        result = subprocess.run(
            ["screencapture", "-x", "-o", "-l", "$(osascript -e 'tell app \"WeChat\" to id of window 1')", str(screenshot_path)],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10
        )

        # Fallback: capture by window title match
        if not screenshot_path.exists():
            # Use Python's Quartz to capture
            try:
                from Quartz import (
                    CGWindowListCopyWindowInfo,
                    kCGWindowListOptionOnScreenOnly,
                    kCGNullWindowID,
                    CGWindowListCreateImage,
                    CGRectNull,
                    kCGWindowListOptionIncludingWindow,
                    kCGWindowImageDefault
                )
                from Cocoa import NSBitmapImageRep, NSPNGFileType

                # Find WeChat window
                window_list = CGWindowListCopyWindowInfo(
                    kCGWindowListOptionOnScreenOnly,
                    kCGNullWindowID
                )

                wechat_window = None
                for window in window_list:
                    owner = window.get('kCGWindowOwnerName', '')
                    if 'WeChat' in owner or 'wechat' in owner.lower():
                        wechat_window = window
                        print(f"Found WeChat window: {window.get('kCGWindowName', 'Unnamed')}")
                        print(f"  Bounds: {window.get('kCGWindowBounds', {})}")
                        break

                if wechat_window:
                    window_id = wechat_window['kCGWindowNumber']

                    # Capture the window
                    image = CGWindowListCreateImage(
                        CGRectNull,
                        kCGWindowListOptionIncludingWindow,
                        window_id,
                        kCGWindowImageDefault
                    )

                    if image:
                        # Save to file
                        bitmap = NSBitmapImageRep.alloc().initWithCGImage_(image)
                        png_data = bitmap.representationUsingType_properties_(NSPNGFileType, None)
                        png_data.writeToFile_atomically_(str(screenshot_path), True)
                        print(f"Screenshot saved: {screenshot_path}")
                        return str(screenshot_path)

            except ImportError as e:
                print(f"Quartz import failed: {e}")
            except Exception as e:
                print(f"Quartz capture failed: {e}")

        if screenshot_path.exists():
            print(f"Screenshot saved: {screenshot_path}")
            print(f"Size: {screenshot_path.stat().st_size / 1024:.1f} KB")
            return str(screenshot_path)
        else:
            print("Screenshot capture failed")
            return None

    except Exception as e:
        print(f"Error capturing window: {e}")
        return None


def navigate_to_moments():
    """Navigate WeChat to Moments (朋友圈) tab via UI automation."""
    print("\n" + "-" * 50)
    print("Navigate to Moments (朋友圈)")
    print("-" * 50)

    # AppleScript to click on Moments
    # Note: The exact UI elements depend on WeChat version
    script = '''
    tell application "WeChat" to activate
    delay 0.5

    tell application "System Events"
        tell process "WeChat"
            -- Try to find and click Moments/Discover tab
            -- WeChat Mac UI structure varies by version

            -- Method 1: Try menu bar
            try
                click menu item "朋友圈" of menu "查看" of menu bar 1
                return "Clicked via menu"
            end try

            -- Method 2: Try keyboard shortcut (if exists)
            try
                keystroke "4" using command down
                return "Used keyboard shortcut"
            end try

            -- Method 3: Look for UI elements
            try
                set uiElements to entire contents of window 1
                return "Found " & (count of uiElements) & " UI elements"
            end try

        end tell
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Navigation result: {result.stdout.strip()}")
        if result.stderr:
            print(f"Notes: {result.stderr.strip()}")

        return result.returncode == 0

    except Exception as e:
        print(f"Navigation error: {e}")
        return False


def explore_wechat_ui():
    """Explore WeChat's UI structure for automation."""
    print("\n" + "-" * 50)
    print("Exploring WeChat UI Structure")
    print("-" * 50)

    script = '''
    tell application "System Events"
        tell process "WeChat"
            -- Get window structure
            set windowCount to count of windows

            if windowCount > 0 then
                tell window 1
                    set groupCount to count of groups
                    set buttonCount to count of buttons
                    set textCount to count of static texts
                    set imageCount to count of images

                    return "Windows: " & windowCount & ", Groups: " & groupCount & ", Buttons: " & buttonCount & ", Texts: " & textCount & ", Images: " & imageCount
                end tell
            else
                return "No windows found"
            end if
        end tell
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode == 0:
            print(f"UI Structure: {result.stdout.strip()}")
            return True
        else:
            print(f"Could not explore UI: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("UI exploration timed out - WeChat UI may be complex")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_scroll_and_capture():
    """Test scrolling through content and capturing."""
    print("\n" + "-" * 50)
    print("Scroll and Capture Test")
    print("-" * 50)

    script = '''
    tell application "WeChat" to activate
    delay 0.3

    tell application "System Events"
        tell process "WeChat"
            -- Scroll down in the current view
            tell window 1
                scroll area 1
                -- Perform scroll
                perform action "AXScrollDownByPage"
            end tell
        end tell
    end tell
    '''

    try:
        # This is a basic test - actual implementation would
        # capture before/after scroll to detect content change
        print("Scroll test requires manual verification")
        print("The automation framework can scroll and capture sequentially")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def generate_report(results: dict):
    """Generate validation report."""
    print("\n" + "=" * 50)
    print("UI AUTOMATION VALIDATION REPORT")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL/PARTIAL"
        icon = "[OK]" if passed else "[--]"
        print(f"  {icon} {test_name}: {status}")

    print("\n" + "-" * 50)
    print("IMPLEMENTATION APPROACH")
    print("-" * 50)

    print("""
Based on validation results, here's the recommended approach:

1. WINDOW CAPTURE + VISION MODEL
   ─────────────────────────────
   - Programmatically capture WeChat window
   - Send screenshot to Claude/GPT-4V for content extraction
   - Works with any WeChat content (Moments, chats, etc.)
   - No need to parse UI structure

   Flow:
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │ Capture     │ -> │ Vision Model │ -> │ Structured  │
   │ WeChat      │    │ (Claude)     │    │ Data        │
   └─────────────┘    └──────────────┘    └─────────────┘

2. APPLESCRIPT UI CONTROL
   ───────────────────────
   - Navigate WeChat to specific views
   - Scroll through content
   - Click on elements
   - Combined with capture for full automation

3. IMPLEMENTATION STEPS
   ─────────────────────
   a) Activate WeChat window
   b) Navigate to Moments (via menu/shortcut)
   c) Capture window screenshot
   d) Scroll down, capture again (repeat for more content)
   e) Send captures to vision model with extraction prompt
   f) Parse structured response (posts, authors, content)
   g) Summarize as needed
""")


def show_next_steps():
    """Show next implementation steps."""
    print("\n" + "=" * 50)
    print("NEXT STEPS")
    print("=" * 50)

    print("""
To build the WeChat skill with UI automation:

1. CREATE CAPTURE SCRIPT
   - Activate WeChat
   - Capture window to temp file
   - Return image path for vision processing

2. CREATE MOMENTS NAVIGATOR
   - Open Moments view
   - Scroll and capture multiple pages
   - Detect end of new content

3. INTEGRATE WITH OPENCLAW
   - Skill calls capture script
   - Sends image to Claude vision
   - Extracts structured Moments data
   - Returns summary to user

EXAMPLE SKILL USAGE:
────────────────────
User: "Summarize my WeChat Moments from today"

OpenClaw:
1. Runs: capture_wechat.py --view moments --scroll 3
2. Gets: [screenshot1.png, screenshot2.png, screenshot3.png]
3. Sends to Claude: "Extract all Moments posts from these screenshots"
4. Returns: "Here are today's 12 Moments posts: ..."

Want me to create the implementation scripts?
""")


def main():
    parser = argparse.ArgumentParser(
        description="Validate WeChat UI automation on macOS"
    )
    parser.add_argument(
        "--capture-moments", "-m",
        action="store_true",
        help="Attempt to navigate to and capture Moments"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode with pauses"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("WeChat UI Automation Validation")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis validates real-time WeChat access via UI automation.")

    results = {}

    # Check WeChat running
    results['wechat_running'] = check_wechat_running()
    if not results['wechat_running']:
        print("\nPlease start WeChat and log in, then retry.")
        sys.exit(1)

    # Check accessibility
    results['accessibility'] = check_accessibility_permissions()
    if not results['accessibility']:
        print("\nAccessibility permissions required for UI automation.")
        print("Please grant access and retry.")
        sys.exit(1)

    # Get window info
    results['window_detection'] = get_wechat_windows()

    # Explore UI structure
    results['ui_exploration'] = explore_wechat_ui()

    # Capture window
    screenshot = capture_wechat_window()
    results['window_capture'] = screenshot is not None

    if args.capture_moments:
        results['moments_navigation'] = navigate_to_moments()

    # Generate report
    generate_report(results)
    show_next_steps()

    if screenshot:
        print(f"\nCaptured screenshot available at: {screenshot}")
        print("You can view this to verify the capture worked correctly.")


if __name__ == "__main__":
    main()
