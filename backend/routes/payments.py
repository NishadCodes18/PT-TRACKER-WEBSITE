from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from ..database import db
from ..models import Client, Expense, Payment, Trainer

payments_bp = Blueprint("payments", __name__, url_prefix="/api")


def add_months(sourcedate, months):
    return sourcedate + timedelta(days=months * 30)


def add_sessions(start_date, sessions, session_days):
    valid_days = [0, 2, 4] if session_days == "MWF" else [1, 3, 5]
    current_date = start_date
    sessions_remaining = sessions
    while sessions_remaining > 0:
        if current_date.weekday() in valid_days:
            sessions_remaining -= 1
            if sessions_remaining == 0:
                break
        current_date += timedelta(days=1)
    return current_date


@payments_bp.route("/payments", methods=["GET"])
@login_required
def get_payments():
    """Get payments with optional pagination, date range, and search."""
    query = Payment.query
    if not getattr(current_user, "is_admin", False):
        query = query.filter_by(trainer_id=current_user.id)

    q = (request.args.get("q") or "").strip()
    if q:
        text_q = f"%{q}%"
        query = query.filter(
            Payment.description.ilike(text_q)
            | Payment.client.has(name=Client.name.ilike(text_q))
        )

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    if from_date:
        try:
            query = query.filter(Payment.payment_date >= datetime.strptime(from_date, "%Y-%m-%d").date())
        except ValueError:
            return jsonify({"error": "Invalid from_date format"}), 400
    if to_date:
        try:
            query = query.filter(Payment.payment_date <= datetime.strptime(to_date, "%Y-%m-%d").date())
        except ValueError:
            return jsonify({"error": "Invalid to_date format"}), 400

    query = query.order_by(Payment.payment_date.desc())

    paginated = request.args.get("paginated", "1") != "0"
    if not paginated:
        payments = query.all()
        return jsonify(
            [
                {
                    "id": p.id,
                    "client_id": p.client_id,
                    "client_name": p.client.name if p.client else "Unknown",
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "payment_mode": p.payment_mode,
                    "gym_payment_done": p.gym_payment_done,
                    "gym_payment_amount": float(p.gym_payment_amount) if p.gym_payment_amount else None,
                    "description": p.description,
                }
                for p in payments
            ]
        )

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 5), 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        {
            "items": [
                {
                    "id": p.id,
                    "client_id": p.client_id,
                    "client_name": p.client.name if p.client else "Unknown",
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "payment_mode": p.payment_mode,
                    "gym_payment_done": p.gym_payment_done,
                    "gym_payment_amount": float(p.gym_payment_amount) if p.gym_payment_amount else None,
                    "description": p.description,
                }
                for p in items
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": max((total + per_page - 1) // per_page, 1),
                "has_next": (page * per_page) < total,
                "has_prev": page > 1,
            },
        }
    )


@payments_bp.route("/payments", methods=["POST"])
@login_required
def create_payment():
    data = request.get_json() or {}
    is_admin = getattr(current_user, "is_admin", False)

    client_id = data.get("client_id")
    amount = data.get("amount")
    payment_date_str = data.get("payment_date")
    description = data.get("description", "").strip()
    duration_months = int(data.get("duration_months", 1))
    plan_type = data.get("plan_type", "monthly")
    session_days = data.get("session_days", "MWF")
    start_date_str = data.get("start_date") or payment_date_str
    payment_mode = data.get("payment_mode", "cash").strip().lower()
    gym_payment_done = bool(data.get("gym_payment_done", False))
    gym_payment_amount = data.get("gym_payment_amount")

    if not client_id or not amount or not payment_date_str:
        return jsonify({"error": "Client, amount, and date are required"}), 400

    if payment_mode not in ("cash", "online", "upi", "card", "bank_transfer", "split"):
        return jsonify({"error": "Invalid payment mode"}), 400

    client_query = Client.query.filter_by(id=client_id)
    if not is_admin:
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()

    try:
        amount = float(amount)
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date or amount format"}), 400

    total_amount = amount * duration_months
    trainer_id = current_user.id if not is_admin else client.trainer_id

    payment = Payment(
        client_id=client_id,
        trainer_id=trainer_id,
        amount=total_amount,
        payment_date=payment_date,
        start_date=start_date,
        plan_type=plan_type,
        payment_mode=payment_mode,
        gym_payment_done=gym_payment_done,
        gym_payment_amount=float(gym_payment_amount) if gym_payment_amount else None,
        description=description,
    )

    if plan_type == "session":
        client.renewal_date = add_sessions(start_date, duration_months, session_days)
    else:
        client.renewal_date = add_months(start_date, duration_months)

    db.session.add(payment)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create payment: {str(e)}"}), 500

    return jsonify(
        {
            "id": payment.id,
            "client_id": payment.client_id,
            "client_name": payment.client.name,
            "amount": float(payment.amount),
            "payment_date": payment.payment_date.isoformat(),
            "payment_mode": payment.payment_mode,
            "gym_payment_done": payment.gym_payment_done,
            "gym_payment_amount": float(payment.gym_payment_amount) if payment.gym_payment_amount else None,
            "description": payment.description,
        }
    ), 201


@payments_bp.route("/payments/<int:payment_id>", methods=["DELETE"])
@login_required
def delete_payment(payment_id):
    payment_query = Payment.query.filter_by(id=payment_id)
    if not getattr(current_user, "is_admin", False):
        payment_query = payment_query.filter_by(trainer_id=current_user.id)
    payment = payment_query.first_or_404()

    db.session.delete(payment)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete payment: {str(e)}"}), 500
    return "", 204


@payments_bp.route("/expenses", methods=["GET"])
@login_required
def get_expenses():
    query = Expense.query
    if not getattr(current_user, "is_admin", False):
        query = query.filter_by(trainer_id=current_user.id)

    category = (request.args.get("category") or "").strip()
    if category:
        query = query.filter_by(category=category)

    query = query.order_by(Expense.expense_date.desc())

    paginated = request.args.get("paginated", "1") != "0"
    if not paginated:
        expenses = query.all()
        return jsonify(
            [
                {
                    "id": e.id,
                    "expense_name": e.expense_name,
                    "category": e.category,
                    "amount": float(e.amount),
                    "expense_date": e.expense_date.isoformat(),
                }
                for e in expenses
            ]
        )

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 5), 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        {
            "items": [
                {
                    "id": e.id,
                    "expense_name": e.expense_name,
                    "category": e.category,
                    "amount": float(e.amount),
                    "expense_date": e.expense_date.isoformat(),
                }
                for e in items
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": max((total + per_page - 1) // per_page, 1),
                "has_next": (page * per_page) < total,
                "has_prev": page > 1,
            },
        }
    )


@payments_bp.route("/expenses", methods=["POST"])
@login_required
def create_expense():
    data = request.get_json() or {}
    is_admin = getattr(current_user, "is_admin", False)

    expense_name = data.get("expense_name", "").strip()
    category = data.get("category", "other").strip()
    amount = data.get("amount")
    expense_date_str = data.get("expense_date")

    if not expense_name or not amount or not expense_date_str:
        return jsonify({"error": "Expense name, amount, and date are required"}), 400

    try:
        amount = float(amount)
        expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount or date format"}), 400

    trainer_id = current_user.id
    if is_admin:
        requested_trainer_id = data.get("trainer_id")
        if requested_trainer_id:
            trainer = Trainer.query.get(requested_trainer_id)
            if not trainer:
                return jsonify({"error": "Invalid trainer_id"}), 400
            trainer_id = trainer.id
        else:
            trainer = Trainer.query.order_by(Trainer.id).first()
            if not trainer:
                return jsonify({"error": "No trainer accounts available. Create a trainer first."}), 400
            trainer_id = trainer.id

    expense = Expense(
        trainer_id=trainer_id,
        expense_name=expense_name,
        amount=amount,
        category=category,
        expense_date=expense_date,
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify(
        {
            "id": expense.id,
            "expense_name": expense.expense_name,
            "category": expense.category,
            "amount": float(expense.amount),
            "expense_date": expense.expense_date.isoformat(),
        }
    ), 201


@payments_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    expense_query = Expense.query.filter_by(id=expense_id)
    if not getattr(current_user, "is_admin", False):
        expense_query = expense_query.filter_by(trainer_id=current_user.id)
    expense = expense_query.first_or_404()

    db.session.delete(expense)
    db.session.commit()
    return "", 204


@payments_bp.route("/reports/monthly", methods=["GET"])
@login_required
def monthly_revenue_report():
    """Revenue report grouped by month for charting."""
    months = min(max(request.args.get("months", 6, type=int), 1), 24)
    start_date = datetime.utcnow().date() - timedelta(days=months * 30)

    query = (
        db.session.query(Payment.payment_date, func.sum(Payment.amount).label("amount"))
        .filter(Payment.payment_date >= start_date)
        .group_by(Payment.payment_date)
        .order_by(Payment.payment_date)
    )
    if not getattr(current_user, "is_admin", False):
        query = query.filter(Payment.trainer_id == current_user.id)

    rows = query.all()
    timeline = [{"date": d.isoformat(), "amount": float(a or 0)} for d, a in rows]
    total = round(sum(item["amount"] for item in timeline), 2)

    return jsonify({"timeline": timeline, "total": total, "months": months})


EXPENSE_CATEGORIES = [
    ("gym_cut", "Gym Commission Cut"),
    ("supplements", "Supplements for Client"),
    ("travel", "Travel Expense"),
    ("equipment", "Equipment/Gear"),
    ("certification", "Certification/Course"),
    ("other", "Other"),
]
