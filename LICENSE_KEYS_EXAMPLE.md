# Example License Keys for PT Tracker Registration

This file contains example license keys that can be distributed to users who want to register for the PT Tracker system.

**Contact for License Keys**: nishadpatil2008@gmail.com

---

## Example License Keys (For Testing/Demo)

These are sample license keys. Replace these with real keys generated using `scripts/generate_licenses.py`:

```
DEMO-ABCD-1234-EFGH
TEST-WXYZ-5678-IJKL
SAMPLE-9012-MNOP-QRST
```

---

## How to Generate Real License Keys

### Step 1: Create the License Keys Table

Run this command to create the database table:

```bash
python scripts/create_license_table.py
```

### Step 2: Generate License Keys

Generate 10 license keys:

```bash
python scripts/generate_licenses.py 10
```

Generate 50 license keys with custom notes:

```bash
python scripts/generate_licenses.py 50 "Batch for June 2026"
```

---

## How to Use License Keys

1. **Distribution**: Send license keys to authorized users via email
2. **Registration**: Users enter the license key during account registration
3. **One-time Use**: Each key can only be used once
4. **Tracking**: Admin can see which keys are used and by whom

---

## For Administrators

### View All License Keys

Use the admin panel or run database queries to view all license keys:

```python
# In Python shell
from backend.models_license import LicenseKey
from backend.database import db

# List all unused keys
unused = LicenseKey.query.filter_by(is_used=False).all()
for key in unused:
    print(key.license_key)

# List all used keys
used = LicenseKey.query.filter_by(is_used=True).all()
for key in used:
    print(f"{key.license_key} - Used by trainer ID: {key.used_by_trainer_id}")
```

---

## Security Notes

- Keep license keys confidential
- Distribute keys only to authorized users
- Monitor key usage regularly
- Revoke access if keys are compromised
- Generate new batches as needed

---

**Software Developer**: Nishad Patil  
**Contact**: nishadpatil2008@gmail.com
