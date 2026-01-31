# WeChat Skill - Authentication Validation

This directory contains validation scripts to test WeChat data access before building the full skill.

## Platform-Specific Approaches

| Approach | Platform | Moments Access | Script |
|----------|----------|----------------|--------|
| itchat (Web API) | Any | No | `validate_auth.py` |
| WeChatFerry | Windows | Yes | `validate_wcferry.py` |
| Mac Local DB | macOS | Limited | `validate_mac.py` |
| iPhone Backup | macOS | Yes | `validate_iphone_backup.py` |

---

## macOS Users (Recommended Path)

Since WeChat Web is blocked for many accounts and WeChatFerry is Windows-only, macOS users should try:

### Option 1: iPhone Backup Method (Best for Moments)

If you have an iPhone with WeChat:

```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_iphone_backup.py --list-backups
```

**Setup Steps:**
1. Connect iPhone to Mac via USB
2. Open Finder → Select iPhone
3. Under Backups, **uncheck** "Encrypt local backup"
4. Click "Back Up Now"
5. Run the validation script

### Option 2: Mac Local Database

Check if WeChat Mac has accessible data:

```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_mac.py --find-db
```

---

## Windows Users

### WeChatFerry (Desktop Hook)

**Pros:**
- **CAN access Moments (朋友圈)**
- Full message database access
- More features available

**Cons:**
- Requires WeChat Desktop running
- More complex setup
- Higher TOS risk

**Run:**
```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_wcferry.py --test-moments
```

---

## All Platforms

### itchat (Web API)

**Note:** Many accounts have Web WeChat disabled. Try this first to check.

**Run:**
```bash
cd /home/user/openclaw/skills/wechat/scripts
uv run validate_auth.py
```

If you see "service unavailable for this account" after scanning QR code, your account has Web access disabled.

---

## Decision Matrix

```
Do you need Moments access?
│
├─ NO → Try itchat (validate_auth.py)
│       └─ If blocked → Use manual chat export
│
└─ YES → What's your platform?
         │
         ├─ Windows → Use WeChatFerry (validate_wcferry.py)
         │
         └─ macOS → Do you have iPhone?
                    │
                    ├─ YES → Use iPhone Backup (validate_iphone_backup.py)
                    │
                    └─ NO → Options:
                            1. Screenshot + OCR approach
                            2. Mac local DB (limited)
                            3. WeChat Work API (if enterprise)
```

---

## Alternative Approaches

If automated access doesn't work:

### Manual Chat Export
- WeChat → Settings → General → Export Chat History
- Skill parses exported HTML/text files

### Screenshot + Vision Model
- Screenshot Moments feed on phone
- Use vision model (GPT-4V, Claude) to extract and summarize
- Quick and effective for occasional use

### WeChat Work API
- If you have enterprise WeChat Work account
- Official API with proper access
- Limited to work account data

---

## Troubleshooting

### "Service unavailable for this account"
Your account has WeChat Web disabled. This is common for:
- Accounts created after ~2017
- Accounts in mainland China
- Accounts flagged for security

**Solution:** Use platform-specific alternatives (iPhone backup, WeChatFerry)

### Encrypted iPhone Backup
- Must use **unencrypted** backup for direct access
- Finder → iPhone → Backups → Uncheck "Encrypt local backup"

### WeChat Desktop Not Found (Mac)
- Install from Mac App Store or weixin.qq.com
- Make sure you've logged in at least once
