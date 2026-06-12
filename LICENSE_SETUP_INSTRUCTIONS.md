# License Key System - Setup Instructions

This guide explains how to set up and use the license key system for your PT Tracker application.

---

## What Changed?

1. **License Key Required for Registration**: Users now need a valid license key to create an account
2. **Contact Email Added**: Your email (nishadpatil2008@gmail.com) is now visible on all pages
3. **Email Templates Fixed**: All email templates now use your contact email as support email

---

## Setup Steps

### 1. Create the License Keys Database Table

Run this command in your terminal:

```bash
python scripts/create_license_table.py
```

This creates the `license_keys` table in your database.

### 2. Generate License Keys

Generate 10 license keys:

```bash
python scripts/generate_licenses.py 10
```

Generate 50 keys with notes:

```bash
python scripts/generate_licenses.py 50 "June 2026 batch"
```

The keys will be printed in the terminal. Copy and distribute them to authorized users.

### 3. Distribute Keys to Users

Send license keys to users who should have access. Each key can only be used once.

Example key format: `ABCD-1234-EFGH-5678`

---

## How Users Register

1. Go to the registration page
2. Enter their license key (required field, shown first)
3. Fill in username, email, and password
4. Submit the form

If the license key is invalid or already used, registration will be rejected.

---

## Managing License Keys

### Check Unused Keys

```python
from backend.models_license import LicenseKey
from backend.database import db

# List unused keys
unused = LicenseKey.query.filter_by(is_used=False).all()
for key in unused:
    print(key.license_key)
```

### Check Used Keys

```python
# List used keys with trainer info
used = LicenseKey.query.filter_by(is_used=True).all()
for key in used:
    print(f"{key.license_key} - Trainer ID: {key.used_by_trainer_id} - Used: {key.used_at}")
```

---

## Testing

1. Generate a few test keys
2. Try registering with a valid key (should work)
3. Try registering with an invalid key (should fail)
4. Try registering with the same key twice (should fail on second attempt)

---

## Files Modified

- `templates/login.html` - Added contact email
- `templates/register.html` - Added license key field and contact email
- `templates/forgot_password.html` - Added contact email
- `templates/verify_reset_otp.html` - Added contact email
- `templates/reset_password.html` - Added contact email
- `templates/dashboard.html` - Added contact email in footer
- `backend/models_license.py` - New file: License key model
- `backend/routes/auth.py` - Updated registration to validate license keys
- `backend/utils/email_context.py` - Changed support_email to nishadpatil2008@gmail.com
- `backend/templates/emails/welcome_new.html` - Made contact email clickable

## Files Created

- `LICENSE_KEYS_EXAMPLE.md` - Documentation for license keys
- `scripts/create_license_table.py` - Script to create license table
- `scripts/generate_licenses.py` - Script to generate license keys

---

**Developer**: Nishad Patil  
**Contact**: nishadpatil2008@gmail.com
