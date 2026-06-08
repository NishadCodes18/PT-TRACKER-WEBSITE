from datetime import datetime

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..database import db
from ..models import ADMIN_DATA_OWNER_USERNAME, Client, Trainer, get_or_create_default_admin_trainer
from ..utils.client_emails import send_client_welcome_email
from ..utils.indian_helpers import normalize_phone_number, validate_indian_phone

clients_bp = Blueprint("clients", __name__, url_prefix="/api/clients")


def _is_admin():
    return getattr(current_user, "is_admin", False)


def _trainer_display_name(trainer):
    if not trainer:
        return None
    if trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return "Admin"
    return trainer.username


def _serialize_client(client):
    return {
        "id": client.id,
        "trainer_id": client.trainer_id,
        "trainer_username": _trainer_display_name(client.trainer),
        "name": client.name,
        "contact_number": client.contact_number or "N/A",
        "status": client.status,
        "pt_tier": client.pt_tier,
        "time_slot": client.time_slot,
        "gym_name": client.gym_name,
        "email": client.email,
        "send_email_reminders": client.send_email_reminders,
        "expected_amount": client.expected_amount,
        "renewal_date": client.renewal_date.isoformat() if client.renewal_date else None,
        "notes": client.notes,
        "is_overdue": bool(
            client.renewal_date
            and client.renewal_date < datetime.utcnow().date()
            and client.status == "ongoing"
        ),
    }


def _resolve_trainer(requested_trainer_id=None):
    if requested_trainer_id in (None, ""):
        trainer = Trainer.query.filter(Trainer.username != ADMIN_DATA_OWNER_USERNAME).order_by(Trainer.id).first()
        if trainer:
            return trainer
        return get_or_create_default_admin_trainer()

    try:
        requested_trainer_id = int(requested_trainer_id)
    except (TypeError, ValueError):
        return None

    trainer = Trainer.query.get(requested_trainer_id)
    if not trainer or trainer.username == ADMIN_DATA_OWNER_USERNAME:
        return None
    return trainer


def _client_query():
    return Client.query.options(joinedload(Client.trainer))


def _apply_client_filters(query, *, status_filter=None, search_query=None, tier=None, overdue_only=False):
    if status_filter in ("ongoing", "lost"):
        query = query.filter(Client.status == status_filter)

    if tier:
        query = query.filter(Client.pt_tier == tier)

    if search_query:
        q = f"%{search_query.strip()}%"
        query = query.filter(
            or_(
                Client.name.ilike(q),
                Client.contact_number.ilike(q),
                Client.email.ilike(q),
                Client.notes.ilike(q),
            )
        )

    if overdue_only:
        today = datetime.utcnow().date()
        query = query.filter(Client.status == "ongoing", Client.renewal_date.isnot(None), Client.renewal_date < today)

    return query


def _apply_sort(query, sort_by, sort_order):
    sort_order = "desc" if sort_order == "desc" else "asc"
    col = {
        "name": Client.name,
        "renewal_date": Client.renewal_date,
        "created_at": Client.created_at,
    }.get(sort_by, Client.name)

    return query.order_by(col.desc() if sort_order == "desc" else col.asc())


@clients_bp.route("", methods=["GET"])
@login_required
def get_clients():
    """Get clients with optional server-side filtering and pagination."""
    is_admin = _is_admin()
    query = _client_query()
    if not is_admin:
        query = query.filter(Client.trainer_id == current_user.id)

    query = _apply_client_filters(
        query,
        status_filter=request.args.get("status"),
        search_query=request.args.get("q", ""),
        tier=request.args.get("pt_tier"),
        overdue_only=(request.args.get("overdue") == "1"),
    )
    query = _apply_sort(query, request.args.get("sort_by", "name"), request.args.get("sort_order", "asc"))

    paginated = request.args.get("paginated", "1") != "0"
    if not paginated:
        clients = query.all()
        return jsonify([_serialize_client(c) for c in clients])

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(max(per_page, 5), 100)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        {
            "items": [_serialize_client(c) for c in items],
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


@clients_bp.route("", methods=["POST"])
@login_required
def create_client():
    data = request.get_json() or {}
    is_admin = _is_admin()

    name = data.get("name", "").strip()
    contact_number = data.get("contact_number", "").strip()
    status = data.get("status", "ongoing").strip().lower()
    pt_tier = data.get("pt_tier", "Silver")
    time_slot = data.get("time_slot", "").strip()
    gym_name = data.get("gym_name", "").strip()
    email = data.get("email", "").strip()
    send_email_reminders = bool(data.get("send_email_reminders", False))
    notes = data.get("notes", "").strip()
    renewal_date = None

    if not name:
        return jsonify({"error": "Name is required"}), 400

    if email:
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            return jsonify({"error": "Enter a valid email address"}), 400

    if data.get("renewal_date") not in (None, ""):
        try:
            renewal_date = datetime.strptime(data["renewal_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid renewal date format"}), 400
    if status not in ("ongoing", "lost"):
        return jsonify({"error": "Status must be ongoing or lost"}), 400

    # Validate and normalize Indian phone number
    if contact_number:
        if not validate_indian_phone(contact_number):
            return jsonify({"error": "Invalid Indian phone number format. Please use 10-digit number."}), 400
        contact_number = normalize_phone_number(contact_number)

    if is_admin:
        trainer = _resolve_trainer(data.get("trainer_id"))
        if trainer is None:
            return jsonify({"error": "Invalid trainer_id"}), 400
    else:
        trainer = current_user

    client = Client(
        trainer=trainer,
        name=name,
        contact_number=contact_number,
        status=status,
        pt_tier=pt_tier,
        time_slot=time_slot,
        gym_name=gym_name,
        email=email,
        send_email_reminders=send_email_reminders,
        renewal_date=renewal_date,
        notes=notes,
    )

    db.session.add(client)
    db.session.commit()

    welcome_email_sent = False
    email_message = None
    if client.email:
        welcome_email_sent = send_client_welcome_email(client)
        if welcome_email_sent:
            email_message = f"Client created successfully! Welcome email sent to {client.email}"
        else:
            email_message = f"Client created successfully, but welcome email could not be sent to {client.email}. Check SMTP settings."
    else:
        email_message = "Client created successfully!"

    payload = _serialize_client(client)
    payload["welcome_email_sent"] = welcome_email_sent
    payload["message"] = email_message
    return jsonify(payload), 201


@clients_bp.route("/<int:client_id>", methods=["GET"])
@login_required
def get_client(client_id):
    client_query = _client_query().filter_by(id=client_id)
    if not _is_admin():
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()
    return jsonify(_serialize_client(client))


@clients_bp.route("/<int:client_id>", methods=["PUT"])
@login_required
def update_client(client_id):
    client_query = _client_query().filter_by(id=client_id)
    is_admin = _is_admin()
    if not is_admin:
        client_query = client_query.filter_by(trainer_id=current_user.id)
    client = client_query.first_or_404()

    data = request.get_json() or {}

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            return jsonify({"error": "Name is required"}), 400
        client.name = name
    if "contact_number" in data:
        contact_number = str(data["contact_number"] or "").strip()
        if contact_number and not validate_indian_phone(contact_number):
            return jsonify({"error": "Invalid Indian phone number format"}), 400
        client.contact_number = normalize_phone_number(contact_number) if contact_number else None
    if "status" in data:
        status = str(data["status"]).strip().lower()
        if status not in ("ongoing", "lost"):
            return jsonify({"error": "Status must be ongoing or lost"}), 400
        client.status = status
    if "pt_tier" in data:
        client.pt_tier = data["pt_tier"]
    if "time_slot" in data:
        client.time_slot = str(data["time_slot"] or "").strip()
    if "gym_name" in data:
        client.gym_name = str(data["gym_name"] or "").strip()
    if "email" in data:
        client.email = str(data["email"] or "").strip()
    if "send_email_reminders" in data:
        client.send_email_reminders = bool(data["send_email_reminders"])
    if "renewal_date" in data:
        if data["renewal_date"] in (None, ""):
            client.renewal_date = None
        else:
            try:
                client.renewal_date = datetime.strptime(data["renewal_date"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400
    if "notes" in data:
        client.notes = str(data["notes"] or "").strip()
    if "trainer_id" in data:
        if not is_admin:
            return jsonify({"error": "Only admins can reassign clients"}), 403
        trainer = _resolve_trainer(data.get("trainer_id"))
        if trainer is None:
            return jsonify({"error": "Invalid trainer_id"}), 400
        client.trainer = trainer

    db.session.commit()
    return jsonify(_serialize_client(client))


@clients_bp.route("/<int:client_id>", methods=["DELETE"])
@login_required
def delete_client(client_id):
    try:
        client_query = Client.query.filter_by(id=client_id)

        # If not admin, restrict to own clients only
        if not _is_admin():
            client_query = client_query.filter_by(trainer_id=current_user.id)

        client = client_query.first_or_404()

        # Manually delete related records that might not cascade properly
        from ..models import (
            Payment, EmailLog, ClientReferral,
            Attendance, Workout, ProgressMetric, GalleryImage,
            Nutrition, Goal, Badge
        )

        # Delete referrals where this client is the referrer
        ClientReferral.query.filter_by(referrer_id=client_id).delete(synchronize_session=False)

        # Update referrals where this client was referred (set to NULL)
        ClientReferral.query.filter_by(referred_client_id=client_id).update({'referred_client_id': None}, synchronize_session=False)

        # Delete gamification
        Badge.query.filter_by(client_id=client_id).delete(synchronize_session=False)
        Goal.query.filter_by(client_id=client_id).delete(synchronize_session=False)

        # Delete tracking records
        Nutrition.query.filter_by(client_id=client_id).delete(synchronize_session=False)
        GalleryImage.query.filter_by(client_id=client_id).delete(synchronize_session=False)
        ProgressMetric.query.filter_by(client_id=client_id).delete(synchronize_session=False)
        Workout.query.filter_by(client_id=client_id).delete(synchronize_session=False)
        Attendance.query.filter_by(client_id=client_id).delete(synchronize_session=False)

        # Delete financial records
        Payment.query.filter_by(client_id=client_id).delete(synchronize_session=False)

        # Delete email logs
        EmailLog.query.filter_by(client_id=client_id).delete(synchronize_session=False)

        # Now delete the client
        db.session.delete(client)
        db.session.commit()

        return "", 204
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting client {client_id}: {error_details}")
        return jsonify({"error": f"Failed to delete client: {str(e)}"}), 500


@clients_bp.route("/search/advanced", methods=["POST"])
@login_required
def advanced_search():
    """Advanced search retained for compatibility with older UI clients."""
    filters = request.json or {}
    query = _client_query()

    if not _is_admin():
        query = query.filter(Client.trainer_id == current_user.id)

    query = _apply_client_filters(
        query,
        status_filter=filters.get("status"),
        search_query=filters.get("name") or filters.get("email") or filters.get("contact_number"),
        tier=filters.get("pt_tier"),
        overdue_only=bool(filters.get("show_overdue")),
    )

    if filters.get("renewal_date_from"):
        try:
            start_date = datetime.strptime(filters["renewal_date_from"], "%Y-%m-%d").date()
            query = query.filter(Client.renewal_date >= start_date)
        except ValueError:
            pass

    if filters.get("renewal_date_to"):
        try:
            end_date = datetime.strptime(filters["renewal_date_to"], "%Y-%m-%d").date()
            query = query.filter(Client.renewal_date <= end_date)
        except ValueError:
            pass

    query = _apply_sort(query, filters.get("sort_by", "name"), filters.get("sort_order", "asc"))

    page = max(int(filters.get("page", 1) or 1), 1)
    per_page = min(max(int(filters.get("per_page", 20) or 20), 5), 100)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        {
            "total": total,
            "pages": max((total + per_page - 1) // per_page, 1),
            "current_page": page,
            "per_page": per_page,
            "clients": [_serialize_client(c) for c in items],
        }
    )
