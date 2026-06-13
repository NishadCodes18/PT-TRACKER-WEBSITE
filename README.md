# 🏋️ Personal Training Gym Tracker

> **Professional PT Management System for Freelance Trainers in India**

**Version:** 1.1  
**Status:** ✅ Production Ready  
**Made by:** Nishad Patil  
**Contact:** nishadpatil2008@gmail.com  
**Last Updated:** June 13, 2026

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env with your database and email credentials

# 3. Run the app
python run.py

# 4. Access at http://localhost:5000
# Default login: adminvenom / adminvenom@123
```

---

## ✨ Key Features

### Client Management
- Add, edit, delete clients with profiles
- Multi-gym support & time slot scheduling
- PT tier system (₹5k/₹8k/₹12k per month)
- Automated renewal tracking & reminders
- Client status tracking (ongoing/lost)

### Payment Tracking
- 7 payment modes (Cash, UPI, Card, Bank Transfer, Online, Cheque, Split)
- Gym payment tracking
- Complete payment history & Excel export
- Monthly & session-based plans

### Email Automation
- Automated renewal reminders (5 days before expiry)
- Manual email sending (individual or bulk)
- Complete email audit trail with delivery tracking
- Duplicate prevention system

### Analytics & Insights
- Revenue trends & income breakdown
- Client retention metrics
- Profit analysis & expense tracking
- Performance monitoring

### Admin Features
- Trainer management & role-based access
- Commission policies & payouts
- System audit logs
- Email delivery statistics

### Export & Reporting
- Excel exports (clients, payments, expenses)
- JSON backup
- Advanced filtering & search

---

## 🛠 Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite / PostgreSQL
- **Frontend:** HTML5, CSS3, JavaScript
- **Auth:** Flask-Login + 2FA
- **Email:** SMTP (Gmail/Brevo/Mailgun)

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Database
DATABASE_URL=sqlite:///gym_tracker.db

# Security
SECRET_KEY=your-random-secret-key

# Email (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# Application
GYM_NAME=Your Gym Name
ADMIN_USERNAME=adminvenom
ADMIN_PASSWORD=adminvenom@123
```

### Gmail App Password Setup

1. Enable 2-Step Verification: [Google Security](https://myaccount.google.com/security)
2. Generate App Password: [App Passwords](https://myaccount.google.com/apppasswords)
3. Copy 16-character password to `SMTP_PASSWORD` in `.env`

---

## 🚀 Deployment

### Vercel (Recommended)

```bash
# 1. Deploy database to Render PostgreSQL (free)
# 2. Deploy app to Vercel (free)
# 3. Set environment variables in Vercel dashboard
# 4. Connect via DATABASE_URL
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Render

```bash
# 1. Push to GitHub
git push origin main

# 2. Deploy via Render Blueprint
# Dashboard → New → Blueprint → Connect repo

# 3. Set environment variables
# Render will auto-configure database and cron jobs
```

---

## 📚 Documentation

- [Loading Page Implementation](LOADING_PAGE.md)
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md)
- [Deployment Guide](DEPLOYMENT.md)
- [License System Setup](LICENSE_SETUP_INSTRUCTIONS.md)
- [Auto Email Setup](AUTO_RENEWAL_EMAILS_GUIDE.md)

---

## 🔧 Recent Updates (v1.1 - June 2026)

### Performance Improvements
- **80-90% faster updates** - Optimized data refresh flow
- Instant UI updates with optimistic rendering
- Sequential loading (primary data first, stats in background)
- Delete operations now feel instant (< 1 second)

### Loading Experience
- Professional loading page during cold starts
- Animated skeleton UI matching app design
- Auto-redirect when database ready
- Works on Vercel + Render deployments

### Removed Features
- BMI Progress Gallery (simplified app, removed unused feature)

---

## 🆘 Troubleshooting

**Emails not sending?**
- Use Gmail App Password (not regular password)
- Enable 2-Step Verification on Google account
- Check Email Logs in dashboard

**Database error?**
- Delete `gym_tracker.db` and restart
- Database will be recreated automatically

**Port already in use?**
- Edit `run.py` to use different port
- Or kill process using port 5000

**Slow performance?**
- Upgrade to PostgreSQL for production
- Enable caching in configuration
- Use Vercel/Render for better infrastructure

---

## 📄 License

Created by **Nishad Patil** © 2026  
Contact: nishadpatil2008@gmail.com

---

**Made with 💪 by Nishad Patil**

### Step 1: Setup Environment

```bash
cp .env.example .env
# Edit .env with your Gmail credentials (see Configuration section below)
```

### Step 2: Run Application

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Run the app
python run.py
```

### Step 3: Setup License Keys

```bash
# Create license table
python scripts/create_license_table.py

# Generate 20 license keys
python scripts/generate_licenses.py 20

# Test the system
python scripts/test_license_system.py
```

### Step 4: Access

```
URL:      http://localhost:5000
Username: adminvenom
Password: adminvenom@123
```

> ⚠️ **Change the default password immediately after first login!**

> 📝 **Note:** Users need a valid license key to register. Distribute the generated keys to authorized users.

---

## ✨ Features (45+)

### 🎯 Client Management
- Add, edit, delete clients with comprehensive profiles
- **License key registration** — secure access control for new users
- **Multi-gym support** — track which gym each client trains at
- PT tier system (Silver ₹5k / Gold ₹8k / Platinum ₹12k per month)
- Renewal date tracking with automated reminders
- Phone validation (10-digit Indian numbers with +91/91/0 prefix support)
- Client status tracking (ongoing/lost)
- Time slot scheduling & notes
- **Expiring members section** — dashboard view of clients expiring within 5 days

### 💳 Payment Tracking
- **7 payment modes**: Cash, UPI, Card, Bank Transfer, Online Gateway, Cheque, Other
- **Gym payment tracking**: Track if payment was made to gym owner + amount
- Flexible plans (Monthly / Session-wise)
- Payment history with complete records & Excel export
- Color-coded gym payment status indicators (✅ Green = Paid, ❌ Red = Pending)

### 📧 Email Notification System
- **Automated renewal reminders** — emails sent 5 days before renewal
- **Expiring members dashboard** — dedicated section showing clients expiring within 5 days
- **Manual email sending** — individual client emails or bulk send to all expiring clients
- **Duplicate prevention** — won't send same reminder twice within 5 days
- **Dual notifications** — both client AND trainer receive emails
- **Complete email audit trail** — full history of all emails sent
- Delivery status tracking (sent/failed) with error logging
- Email statistics API with filtering & pagination
- Color-coded urgency indicators (Red/Orange/Green)

### 📈 Progress Tracking
- Monthly BMI progress gallery (photo uploads)
- Attendance logging (session tracking with duration & notes)
- Workout logging (exercises, sets, reps, weight)
- Fitness metrics (weight, measurements, body composition)
- Fitness goals (goal setting & progress monitoring)

### 🏆 Gamification & Engagement
- Badge system with auto-awards
- Achievement milestones (10 Sessions Streak, 30 Sessions Commitment, Goal Getter, Goal Master, One Year Member)
- Trainer leaderboards (daily/weekly/monthly/yearly)
- Client leaderboards (by attendance, payments, goals)

### 📊 Analytics & Insights
- Revenue analytics & trends (daily/weekly/monthly/yearly)
- Client retention metrics & at-risk identification
- Income breakdown by PT tier
- Expense breakdown by category
- Profit analysis (net profit, profit margins)
- Client Lifetime Value (CLV) calculations
- Attendance trend analysis

### 👥 Admin Features
- **Trainer management** — create/manage multiple trainers
- **Commission policies** — custom payout percentages per trainer
- **Performance monitoring** — track trainer productivity & revenue
- **System audit logs** — complete trail of all system actions
- **User activity logs** — monitor all logins & actions
- **Email statistics** — delivery success rates

### 📤 Data Export & Reporting
- Excel export (clients, payments, expenses)
- PDF reports (comprehensive per-client reports)
- JSON backup (full data backup)

### 🇮🇳 India-Specific Features
- Phone validation (10-digit Indian numbers, auto-normalization)
- Rupee currency (₹) throughout with Indian comma format (₹1,00,000)
- GST calculations (18% standard rate for fitness services)
- Indian payment methods (UPI, Bank Transfer, Cheque, etc.)
- All 28 Indian states + 8 Union Territories
- Updated pricing tiers: ₹5,000 / ₹8,000 / ₹12,000

### 🎨 Professional UI/UX
- Branding: "Personal Training Gym Tracker"
- Logo: 💪 (muscle emoji)
- Modern dark theme with accent colors
- Responsive design for all devices
- Emoji navigation icons & color-coded status indicators
- Professional footer: "Made by Nishad Patil"

---

## 🔐 Security

| Feature | Details |
|---------|---------|
| **License Key System** | Registration requires valid license key (one-time use) |
| **Password Hashing** | PBKDF2-SHA256 |
| **Two-Factor Auth** | TOTP-based 2FA with QR code setup |
| **Access Control** | Role-Based (Admin, Manager, Trainer, Assistant) |
| **Audit Logging** | Complete trail of all user actions |
| **Email Logging** | Full delivery history with error tracking |
| **Session Management** | Secure session handling with timeout |
| **IP Logging** | Track login IP addresses |
| **Key Tracking** | Track which license keys are used and by whom |

### RBAC Permissions

| Action | Admin | Manager | Trainer | Assistant |
|--------|:-----:|:-------:|:-------:|:---------:|
| Manage Trainers | ✅ | ❌ | ❌ | ❌ |
| Manage Payments | ✅ | ✅ | ❌ | ❌ |
| View Reports | ✅ | ✅ | ✅ | ❌ |
| Manage All Clients | ✅ | ✅ | ❌ | ❌ |
| Manage Own Clients | ✅ | ✅ | ✅ | ✅ |
| View Analytics | ✅ | ✅ | ✅ | ❌ |
| Export Data | ✅ | ✅ | ✅ | ❌ |

---

## ⚙️ Configuration

### Environment Variables (`.env`)

Copy `.env.example` to `.env` and configure:

```env
# Application
SECRET_KEY=your-random-secret-key-here
DATABASE_URL=sqlite:///gym_tracker.db
SQLALCHEMY_TRACK_MODIFICATIONS=False
LOG_LEVEL=INFO
SLOW_REQUEST_MS=400

# Email (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-google-app-password

# Automatic Renewal Emails (Cron)
CRON_SECRET=your-cron-secret-here
APP_URL=http://localhost:5000

# Application Settings
GYM_NAME=Your Gym Name
ADMIN_USERNAME=adminvenom
ADMIN_PASSWORD=adminvenom@123

# Optional
MAX_LOGIN_ATTEMPTS=5
SESSION_TIMEOUT=3600
ENABLE_2FA=True
ENABLE_AUDIT_LOGGING=True
```

### Gmail App Password Setup

1. **Enable 2-Step Verification**: Go to [Google Security](https://myaccount.google.com/security) → "2-Step Verification" → Follow prompts
2. **Generate App Password**: Go to [App Passwords](https://myaccount.google.com/apppasswords) → Select "Mail" → Select your device → Click "Generate"
3. **Copy the 16-character password** to `SMTP_PASSWORD` in `.env`

> ⚠️ Use the App Password, **NOT** your regular Gmail password!

### Test Email Configuration

Test manual email sending:
1. Go to dashboard → "Members Expiring Soon" section
2. Click "Send All Renewal Emails" button
3. Check Email Logs to verify delivery

For automatic emails (cron setup required):
```bash
curl -X POST http://localhost:5000/api/cron/send-renewals \
  -H "Authorization: Bearer YOUR_CRON_SECRET"
```

See `AUTO_RENEWAL_EMAILS_GUIDE.md` for complete cron setup instructions.

### Production Deployment Checklist

- [ ] Change `SECRET_KEY` to a cryptographically random string
- [ ] Change default admin credentials
- [ ] Generate license keys for authorized users
- [ ] Set up cron job for automatic renewal emails (see guide)
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Enable HTTPS/SSL
- [ ] Set `LOG_LEVEL=WARNING`
- [ ] Configure proper SMTP service
- [ ] Set up regular database backups
- [ ] Regularly rotate Gmail App Password
- [ ] Set CRON_SECRET for automatic email security

---

## 📁 Project Structure

```
gym-tracker/
├── backend/
│   ├── __init__.py              # App factory + migrations + blueprint registration
│   ├── config.py                # Configuration
│   ├── database.py              # SQLAlchemy setup
│   ├── models.py                # All database models (20+ tables)
│   ├── models_license.py        # License key model
│   ├── routes/
│   │   ├── admin.py             # Admin pages
│   │   ├── admin_management.py  # Trainer management & RBAC
│   │   ├── analytics.py         # Revenue, retention, CLV analytics
│   │   ├── auth.py              # Authentication + License validation
│   │   ├── clients.py           # Client CRUD + advanced search
│   │   ├── dashboard.py         # Dashboard + expiring clients
│   │   ├── email_logs.py        # Email audit trail API
│   │   ├── export.py            # Excel & PDF exports
│   │   ├── gamification.py      # Badges & leaderboards
│   │   ├── payments.py          # Payment tracking
│   │   ├── reminders.py         # Renewal reminders
│   │   ├── cron.py              # Cron endpoints for auto-emails
│   │   ├── security.py          # 2FA, auth, profiles
│   │   └── tracking.py          # Attendance, workouts, progress
│   ├── services/
│   │   └── reminder_service.py  # Email reminder logic
│   └── utils/
│       ├── helpers.py           # 50+ utility functions
│       ├── mail.py              # Email sending
│       ├── email_context.py     # Email template context
│       └── indian_helpers.py    # Indian-specific utilities
│
├── scripts/
│   ├── create_license_table.py # Create license keys table
│   ├── generate_licenses.py     # Generate license keys
│   ├── test_license_system.py   # Test license system
│   └── cron_send_renewals.py    # Cron script for auto-emails
│
├── templates/
│   ├── dashboard.html           # Main dashboard (+ expiring section)
│   ├── login.html               # Login page
│   ├── register.html            # Registration page (+ license field)
│   ├── admin.html               # Admin panel
│   └── ...                      # Other pages
│
├── static/
│   ├── css/style.css            # Professional dark theme
│   └── js/app.js                # Frontend logic (+ email functions)
│
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── run.py                       # Entry point
├── LICENSE_SETUP_INSTRUCTIONS.md    # License system guide
├── AUTO_RENEWAL_EMAILS_GUIDE.md     # Auto-email setup guide
├── FINAL_SUMMARY.txt            # Complete implementation summary
└── gym_tracker.db               # SQLite database (auto-created)
```

---

## 💾 Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `trainers` | User accounts with roles |
| `clients` | Client profiles with gym location |
| `payments` | Payment records with modes & gym tracking |
| `expenses` | Expense records by category |
| `email_logs` | Complete email audit trail |
| `license_keys` | License keys for registration control |

### Tracking Tables

| Table | Purpose |
|-------|---------|
| `attendance` | Session attendance records |
| `workouts` | Exercise logging |
| `progress_metrics` | Body measurements |
| `gallery_images` | Progress photos |
| `nutrition` | Meal tracking |
| `goals` | Fitness goals |

### System Tables

| Table | Purpose |
|-------|---------|
| `badges` | Gamification achievements |
| `client_referrals` | Referral system |
| `audit_logs` | Activity tracking |
| `system_settings` | App configuration |
| `trainer_roles` | RBAC settings |
| `integration_tokens` | OAuth tokens |
| `two_factor_auth` | 2FA setup |

### Key Fields Added

```
Client
└── gym_name (string) — Gym location

Payment
├── payment_mode (string) — Cash/UPI/Card/Bank/Online/Cheque/Other
├── gym_payment_done (boolean) — Payment made to gym?
└── gym_payment_amount (decimal) — Amount paid to gym
```

---

## 🔌 API Documentation

**Base URL:** `http://localhost:5000/api`  
**Authentication:** All endpoints require login (session cookies)  
**Rate Limit:** 100 requests/hour/user

### Analytics (`/api/analytics/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/revenue?months=12` | Revenue trends over time |
| GET | `/analytics/income-by-tier` | Income breakdown by PT tier |
| GET | `/analytics/client-retention` | Retention rate & at-risk clients |
| GET | `/analytics/expense-breakdown?months=12` | Expense analysis by category |
| GET | `/analytics/profit-analysis?months=12` | Net profit & profit margins |
| GET | `/analytics/client-lifetime-value` | CLV rankings |
| GET | `/analytics/attendance-trends/<client_id>?months=3` | Client attendance stats |

<details>
<summary><strong>Example: Revenue Analytics Response</strong></summary>

```json
{
  "total_revenue": 240000.50,
  "transaction_count": 50,
  "average_transaction": 4800.01,
  "timeline": [
    { "date": "2026-04-01", "amount": 20000, "transactions": 5 }
  ]
}
```
</details>

<details>
<summary><strong>Example: Client Retention Response</strong></summary>

```json
{
  "total_clients": 50,
  "active_clients": 45,
  "lost_clients": 5,
  "retention_rate": 90.0,
  "at_risk_count": 3,
  "at_risk_clients": [
    { "id": 1, "name": "John Doe", "renewal_date": "2026-05-05" }
  ]
}
```
</details>

---

### Tracking (`/api/tracking/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tracking/attendance` | Log session attendance |
| GET | `/tracking/attendance/<client_id>?days=30` | Get attendance history |
| POST | `/tracking/workout` | Log workout |
| GET | `/tracking/progress/<client_id>?days=90` | Get progress metrics |
| POST | `/tracking/progress/<client_id>` | Add progress metric |
| GET | `/tracking/goal/<client_id>` | Get goals |
| POST | `/tracking/goal/<client_id>` | Create goal |
| GET | `/tracking/nutrition/<client_id>?date=2026-05-02` | Get nutrition logs |
| POST | `/tracking/nutrition/<client_id>` | Log meal |

<details>
<summary><strong>Example: Log Attendance</strong></summary>

```json
POST /api/tracking/attendance
{
  "client_id": 1,
  "session_date": "2026-05-02",
  "status": "attended",       // attended | missed | rescheduled
  "duration_minutes": 60,
  "notes": "Great session, good progress"
}
```
</details>

<details>
<summary><strong>Example: Log Workout</strong></summary>

```json
POST /api/tracking/workout
{
  "client_id": 1,
  "workout_date": "2026-05-02",
  "exercise_name": "Bench Press",
  "sets": 4,
  "reps": 10,
  "weight_kg": 80,
  "duration_minutes": 30,
  "notes": "Felt strong today"
}
```
</details>

<details>
<summary><strong>Example: Log Nutrition</strong></summary>

```json
POST /api/tracking/nutrition/<client_id>
{
  "meal_date": "2026-05-02",
  "meal_type": "breakfast",    // breakfast | lunch | dinner | snack
  "meal_description": "Omelette with toast",
  "calories": 350,
  "protein_g": 25,
  "carbs_g": 30,
  "fat_g": 15,
  "notes": "Felt good after meal"
}
```
</details>

---

### Export (`/api/export/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/export/clients-excel` | Download clients Excel |
| GET | `/export/payments-excel` | Download payments Excel |
| GET | `/export/expenses-excel` | Download expenses Excel |
| GET | `/export/client-report/<client_id>` | Download client PDF report |

---

### Admin Management (`/api/admin_management/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin_management/trainers` | List all trainers |
| GET | `/admin_management/trainers/<id>/role` | Get trainer role |
| PUT | `/admin_management/trainers/<id>/role` | Update trainer role |
| PUT | `/admin_management/trainers/<id>/status` | Toggle active/inactive |
| GET | `/admin_management/audit-logs?limit=100&action=login` | View audit logs |
| GET | `/admin_management/settings` | Get system settings |
| PUT | `/admin_management/settings` | Update system settings |
| GET | `/admin_management/trainer-performance` | Trainer performance metrics |

<details>
<summary><strong>Example: Update Trainer Role</strong></summary>

```json
PUT /api/admin_management/trainers/<id>/role
{
  "role": "manager",           // admin | manager | trainer | assistant
  "can_manage_trainers": false,
  "can_manage_payments": true,
  "can_view_reports": true,
  "can_manage_all_clients": true
}
```
</details>

---

### Gamification (`/api/gamification/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gamification/badges/<client_id>` | View client badges |
| POST | `/gamification/badges/<client_id>` | Award badge |
| GET | `/gamification/check-achievements/<client_id>` | Auto-award achievements |
| GET | `/gamification/leaderboard?period=monthly&limit=10` | Trainer leaderboard |
| GET | `/gamification/client-leaderboard?metric=attendance&limit=10` | Client leaderboard |

---

### Security (`/api/security/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/security/2fa/setup` | Get 2FA QR code & secret |
| POST | `/security/2fa/verify` | Verify & enable 2FA |
| POST | `/security/2fa/disable` | Disable 2FA |
| GET | `/security/2fa/status` | Check 2FA status |
| POST | `/security/change-password` | Change password |
| GET | `/security/profile` | View profile |
| PUT | `/security/profile` | Update profile |
| GET | `/security/activity-log?limit=50` | Personal activity log |

---

### Client Search (`/api/clients/search/advanced`)

```json
POST /api/clients/search/advanced
{
  "name": "John",
  "status": "ongoing",
  "pt_tier": "Gold",
  "time_slot": "6:00 AM",
  "email": "john@example.com",
  "contact_number": "9876543210",
  "renewal_date_from": "2026-05-01",
  "renewal_date_to": "2026-06-01",
  "show_overdue": false,
  "sort_by": "renewal_date",   // name | renewal_date | created_at
  "sort_order": "asc",
  "page": 1,
  "per_page": 20
}
```

---

### Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "status": 400
}
```

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Server Error |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask (Python) |
| **Database** | SQLite + SQLAlchemy ORM |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Auth** | Flask-Login + 2FA (pyotp) |
| **Email** | SMTP (Gmail compatible) |
| **Excel** | openpyxl |
| **PDF** | ReportLab |
| **QR Codes** | qrcode |
| **OAuth** | google-auth |
| **Crypto** | cryptography |

---

## 🎓 Usage Scenarios

### Scenario 1: Single Freelance Trainer
1. Register account → Add clients across multiple gyms
2. Log payments (choose payment mode) → Track gym payments
3. System sends automated renewal reminders to both you and clients
4. View analytics → Export reports

### Scenario 2: Gym with Multiple Trainers
1. Admin creates trainer accounts → Set commission policies
2. Each trainer manages their own clients
3. Admin monitors trainer performance & system-wide analytics
4. Track all payments across trainers

### Scenario 3: Client Renewal Workflow
1. Client created with gym location & renewal date
2. 5 days before renewal → Automatic email to client AND trainer
3. Email logged in audit trail
4. Trainer can manually send reminders from "Expiring Members" section
5. Payment logged when received → Next renewal date set

---

## 📚 Additional Documentation

| Document | Description |
|----------|-------------|
| `LICENSE_SETUP_INSTRUCTIONS.md` | Complete guide for license key system setup |
| `AUTO_RENEWAL_EMAILS_GUIDE.md` | Complete guide for automatic email setup |
| `FINAL_SUMMARY.txt` | Complete implementation summary |
| `QUICK_START.txt` | Quick setup commands |
| `VERCEL_DEPLOYMENT.md` | Vercel deployment guide |

---

## 🆘 Troubleshooting

### Emails Not Sending
- Verify SMTP credentials in `.env`
- Ensure you're using a Gmail **App Password** (not regular password)
- Confirm 2-Step Verification is enabled on your Google account
- Check Email Logs in dashboard for error details

### Database Error
- Delete `gym_tracker.db` to reset (⚠️ all data will be lost)
- Restart with `python run.py` — database will be re-created

### Port Already in Use
- Edit `run.py` to use a different port
- Or kill the process using port 5000

### Application Won't Start
- Verify Python 3.8+ is installed
- Run `pip install -r requirements.txt`
- Check that `.env` file exists and is configured
- Review console output for error messages

### License Key Issues
- Run `python scripts/create_license_table.py` to create the table
- Generate keys with `python scripts/generate_licenses.py 10`
- Test with `python scripts/test_license_system.py`
- Check that license key is valid and unused

### Cron Job Not Running
- Verify `CRON_SECRET` environment variable is set
- Check that `APP_URL` points to your application
- Test endpoint manually: `curl -X POST https://your-domain/api/cron/send-renewals -H "Authorization: Bearer YOUR_SECRET"`
- See `AUTO_RENEWAL_EMAILS_GUIDE.md` for setup help

---

## 🚀 Deployment Options

This application can be deployed to multiple platforms:

1. **[Vercel](VERCEL_DEPLOYMENT.md)** - Recommended for serverless deployment (free tier available)
2. **[Render](#deployment-to-github--render)** - Alternative with built-in database and cron support

### Quick Comparison

| Feature | Vercel | Render |
|---------|--------|--------|
| **Hosting Type** | Serverless | Traditional Server |
| **Free Tier** | 100 GB-hours/month | 750 hours/month |
| **Cold Starts** | Yes (~1-2s) | After 15min inactivity (~30s) |
| **Database** | External (Render/Supabase) | Built-in PostgreSQL |
| **Cron Jobs** | External or Pro plan | Built-in free |
| **Setup Complexity** | Medium | Easy (Blueprint) |
| **Best For** | Scalable apps | All-in-one solution |

---

## 🚀 Deployment to Vercel (Recommended)

See **[VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)** for complete instructions.

**Quick Steps:**
1. Deploy database to Render PostgreSQL (free)
2. Deploy app to Vercel (free)
3. Connect them via `DATABASE_URL`
4. Set up cron jobs (keep on Render or use Vercel Cron)

---

## 🚀 Deployment to GitHub & Render

### Step 1: Prepare Your Project

1. **Clean up the repository** (already done if you followed this guide)
   ```bash
   # Remove database from git tracking
   git rm --cached gym_tracker.db
   
   # Remove useless migration scripts
   git rm migrate_clients.py migrate_emails.py schema.sql strip_comments.py
   
   # Add all project files
   git add .
   ```

2. **Verify .gitignore** is properly configured
   - `.env` files excluded
   - `__pycache__` directories excluded
   - `*.db` files excluded
   - Virtual environment (`.venv/`) excluded

### Step 2: Push to GitHub

1. **Create a new GitHub repository**
   - Go to [github.com](https://github.com) → Click "+" → "New repository"
   - Name: `gym-tracker` (or your preferred name)
   - Description: "Personal Training Gym Tracker - Professional PT Management System"
   - Visibility: Choose Public or Private
   - **DO NOT** initialize with README (you already have one)
   - Click "Create repository"

2. **Connect local repo to GitHub**
   ```bash
   # If this is your first commit
   git init
   git add .
   git commit -m "Initial commit: Complete gym tracker app with 40+ features"
   
   # Connect to GitHub (replace YOUR_USERNAME and YOUR_REPO)
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git branch -M main
   git push -u origin main
   ```

3. **For subsequent updates**
   ```bash
   git add .
   git commit -m "Your commit message"
   git push
   ```

### Step 3: Deploy to Render

**Option A: Deploy via Blueprint (Recommended - Automated)**

1. **Push your code to GitHub** (complete Step 2 first)

2. **Deploy to Render**
   - Go to [render.com](https://render.com)
   - Sign up / Log in with GitHub
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` and auto-configure everything
   - Click "Apply" to deploy

3. **Configure Environment Variables**
   
   Render will prompt you to set these values:
   
   | Variable | Value | Notes |
   |----------|-------|-------|
   | `SMTP_SERVER` | `smtp.gmail.com` | Email server |
   | `SMTP_USER` | `your-email@gmail.com` | Your Gmail address |
   | `SMTP_PASSWORD` | `your-app-password` | Gmail App Password (16 chars) |
   | `GYM_NAME` | `Your Gym Name` | Displayed in emails |
   | `ADMIN_USERNAME` | `admin` | Change from default! |
   | `ADMIN_PASSWORD` | `SecurePassword123!` | Strong password! |

   Auto-configured variables (no action needed):
   - `SECRET_KEY` - Generated by Render
   - `CRON_SECRET` - Generated by Render
   - `DATABASE_URL` - Postgres connection string

4. **Wait for deployment** (3-5 minutes)
   - Render will build your app
   - Database will be provisioned automatically
   - App will be deployed and live

**Option B: Manual Deployment**

If you don't want to use the blueprint:

1. **Create Web Service**
   - Dashboard → "New" → "Web Service"
   - Connect GitHub repository
   - Configure:
     - **Name**: `gym-tracker`
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`

2. **Create PostgreSQL Database**
   - Dashboard → "New" → "PostgreSQL"
   - **Name**: `gym-tracker-db`
   - Plan: Free
   - After creation, copy the "Internal Database URL"

3. **Add Environment Variables**
   - In Web Service → "Environment" tab
   - Add all variables from Option A table above
   - Add `DATABASE_URL` with the PostgreSQL URL from step 2

4. **Create Cron Job** (for automated renewal emails)
   - Dashboard → "New" → "Cron Job"
   - Connect same repository
   - **Schedule**: `0 4 * * *` (4 AM daily)
   - **Build Command**: `pip install -r requirements.txt`
   - **Command**: `python scripts/cron_send_renewals.py`
   - Add environment variables: `APP_URL`, `CRON_SECRET`

### Step 4: Post-Deployment Setup

1. **Access your app**
   - URL: `https://gym-tracker-xxxxx.onrender.com` (Render provides this)
   - Login with your configured admin credentials

2. **Change default credentials**
   - Go to Profile → Change Password
   - Update admin username if needed

3. **Test email functionality**
   - Add a test client with renewal date 3 days from now
   - Check Email Logs to verify delivery

4. **Configure custom domain** (optional)
   - Render Dashboard → Settings → Custom Domain
   - Add your domain and configure DNS

### Step 5: Monitoring & Maintenance

**Render Free Tier Notes:**
- App sleeps after 15 minutes of inactivity
- First request after sleep takes ~30 seconds to wake up
- 750 hours/month free (enough for one app running 24/7)
- Database limited to 1GB storage

**View Logs:**
```bash
# In Render dashboard
Logs tab → View real-time logs
```

**Database Backups:**
- Render automatically backs up PostgreSQL databases
- Manual backup: Dashboard → Database → "Backups" tab

**Updating Your App:**
```bash
# Make changes locally
git add .
git commit -m "Update: description of changes"
git push

# Render auto-deploys on push (if auto-deploy enabled)
# Or manually deploy: Render Dashboard → Manual Deploy
```

### Troubleshooting Deployment

**Build Fails:**
- Check `requirements.txt` has all dependencies
- Verify Python version in `runtime.txt` is supported by Render (3.8-3.12)
- Check Render build logs for specific errors

**App Won't Start:**
- Verify `wsgi.py` exists and is correctly configured
- Check environment variables are set correctly
- Review Render logs for startup errors

**Database Connection Issues:**
- Ensure `DATABASE_URL` is set correctly
- Verify database service is running
- Check database connection string format

**Emails Not Sending:**
- Verify Gmail App Password is correct (not regular password)
- Check SMTP variables are set correctly
- Enable "Less secure app access" if using old Gmail accounts (not recommended)
- Review Email Logs in dashboard for error details

**Cron Job Not Running:**
- Verify cron service is deployed and running
- Check cron logs in Render dashboard
- Ensure `CRON_SECRET` matches between web service and cron job
- Verify `APP_URL` points to your web service

---

## 📄 License

Created by **Nishad Patil** © 2026  
Contact: nishadpatil2008@gmail.com

---

**Made with 💪 by Nishad Patil**

© 2026 Personal Training Gym Tracker — All Rights Reserved
