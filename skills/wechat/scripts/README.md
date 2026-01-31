# WeChat Skill - Authentication Validation

This directory contains validation scripts to test WeChat data access before building the full skill.

## Two Approaches

### Approach 1: itchat (Web API) - `validate_auth.py`

**Pros:**
- Works on any platform (Linux, macOS, Windows)
- Simple setup - just scan QR code
- Good for contacts, messages, groups

**Cons:**
- **Cannot access Moments (朋友圈)**
- Web WeChat may be disabled for some accounts
- Limited message history

**Run:**
```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_auth.py
```

### Approach 2: WeChatFerry (Desktop Hook) - `validate_wcferry.py`

**Pros:**
- **CAN access Moments (朋友圈)**
- Full message database access
- More features available

**Cons:**
- Windows only (macOS experimental)
- Requires WeChat Desktop running
- More complex setup
- Higher TOS risk

**Run:**
```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_wcferry.py --test-moments
```

## Recommended Testing Order

1. **First, try itchat** (`validate_auth.py`):
   - If you only need contacts/messages, this may be sufficient
   - Simpler and more portable

2. **If you need Moments**, try WeChatFerry (`validate_wcferry.py`):
   - Requires Windows with WeChat Desktop
   - More powerful but more complex

## Expected Results

### validate_auth.py Output

```
WeChat Access Validation Script
==================================================
Test 1: Basic Account Info
--------------------------------------------------
Logged in as: YourName
WeChat ID: wxid_xxx...

Test 2: Contacts Access
--------------------------------------------------
Total contacts found: 150
Sample contacts (first 5):
  1. Friend A
  2. Friend B
  ...

Test 5: Moments (朋友圈) Access
--------------------------------------------------
IMPORTANT FINDING:
The WeChat Web API does NOT support Moments access.
...
```

### validate_wcferry.py Output (if Moments needed)

```
WeChatFerry Validation Script
==================================================
Platform: SUPPORTED
WeChat Desktop: RUNNING
Connection: SUCCESS

Moments (朋友圈) Test
--------------------------------------------------
Moments API: AVAILABLE
...
```

## Next Steps After Validation

Once you confirm which approach works for your use case:

1. **If itchat works** and Moments not needed:
   - Build skill using itchat backend
   - Focus on contacts, messages, groups features

2. **If WeChatFerry works** and Moments needed:
   - Build skill with WeChatFerry backend
   - Document Windows requirement
   - Implement Moments parsing

3. **If neither works well**:
   - Consider manual export workflow
   - Or mobile automation (Appium) as last resort

## Troubleshooting

### itchat Issues

- **QR code not showing**: Try `--light-terminal` flag or check terminal encoding
- **Login fails immediately**: Your account may have Web WeChat disabled
- **Session expires quickly**: This is a WeChat limitation; re-login needed

### WeChatFerry Issues

- **Connection failed**: Ensure WeChat Desktop is running and logged in
- **DLL injection error**: May need to run as administrator
- **Version mismatch**: Check wcferry package version matches your WeChat version
