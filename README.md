# PT Tracker - Personal Trainer CRM & Expense Tracker

A web application for personal trainers to manage clients, track payments, and monitor business expenses.

## Features

- **Multi-User Authentication**: Secure login/registration with password hashing
- **Dashboard**: Real-time stats showing income, active/lost clients, and net profit
- **Client Management**: Add, edit, delete clients with status tracking (ongoing/lost)
- **Renewal Reminders**: See clients with upcoming renewals in the next 7 days
- **Payment Tracking**: Log client payments with dates and descriptions
- **Expense Tracking**: Record business expenses by category

## Project Structure

```
gym-tracker/
├── backend/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database initialization
│   ├── models.py            # SQLAlchemy models
│   └── routes/
│       ├── auth.py          # Login/register routes
│       ├── dashboard.py     # Dashboard stats API
│       ├── clients.py       # Client CRUD API
│       └── payments.py      # Payment/Expense API
├── static/
│   ├── css/style.css        # Main stylesheet
│   └── js/app.js            # Frontend JavaScript
├── templates/
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   └── dashboard.html       # Main dashboard
├── schema.sql               # Database schema
├── app.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or navigate to the project directory:**
   ```bash
   cd gym-tracker
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   - Navigate to: `http://localhost:5000`
   - Register a new account or login

## Configuration

Edit `backend/config.py` to customize settings:

- `SECRET_KEY`: Change this for production!
- `DATABASE_URL`: Switch to PostgreSQL for production:
  ```python
  SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/gym_tracker'
  ```

## Production Deployment

For production deployment:

1. Set a strong `SECRET_KEY` in environment variables
2. Use PostgreSQL instead of SQLite
3. Set `DEBUG = False`
4. Use a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET/POST | User login |
| `/auth/register` | GET/POST | User registration |
| `/auth/logout` | GET | User logout |
| `/api/stats` | GET | Dashboard statistics |
| `/api/clients` | GET/POST | List/Create clients |
| `/api/clients/<id>` | GET/PUT/DELETE | Manage single client |
| `/api/payments` | GET/POST | List/Create payments |
| `/api/expenses` | GET/POST | List/Create expenses |

## Security Features

- Password hashing using Werkzeug (PBKDF2:SHA256)
- Session-based authentication with Flask-Login
- Login-required decorators on all protected routes
- User data isolation (each trainer sees only their own data)
- CSRF protection via Flask-WTF

## License

MIT License - Feel free to use and modify for your business.
