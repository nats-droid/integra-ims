"""
Notification Service
- Due-date zone detection for inspection_plans
- Auto-create notifications (deduped)
- Email stubs (log-only, Resend TODO)
- Cron endpoint helper
"""
import logging
from datetime import datetime, timezone, timedelta

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ── Due Zone Detection ──────────────────────────────────────────────────────

def get_due_zone(final_due_date: str | None) -> str | None:
    """
    Classify inspection plan due date into urgency zone.
    Returns zone string or None if no notification needed.
    """
    if not final_due_date:
        return None

    # Parse date — handle both 'YYYY-MM-DD' and ISO datetime
    if isinstance(final_due_date, str):
        due = datetime.fromisoformat(final_due_date.replace("Z", "+00:00"))
    else:
        due = final_due_date

    # Compare date-only parts
    today = datetime.now(timezone.utc).date()
    due_date = due.date() if hasattr(due, "date") else due

    days_until = (due_date - today).days

    if days_until < 0:
        return "overdue"
    elif days_until <= 7:
        return "due_7"
    elif days_until <= 30:
        return "due_30"
    elif days_until <= 60:
        return "due_60"
    elif days_until <= 90:
        return "due_90"
    else:
        return None


# ── Zone Metadata ───────────────────────────────────────────────────────────

ZONE_TITLES = {
    "overdue": "⚠️ Overdue: {tag}",
    "due_7": "🔴 Due in 7 days: {tag}",
    "due_30": "🟠 Due in 30 days: {tag}",
    "due_60": "🟡 Due in 60 days: {tag}",
    "due_90": "📅 Upcoming: {tag}",
}

ZONE_MESSAGES = {
    "overdue": "Inspection overdue by {days} day(s). Due: {due_date}. Immediate action required.",
    "due_7": "Inspection due in {days} day(s). Due: {due_date}. Schedule immediately.",
    "due_30": "Inspection due in {days} day(s). Due: {due_date}. Plan scheduling soon.",
    "due_60": "Inspection due in {days} day(s). Due: {due_date}. Begin preparation.",
    "due_90": "Inspection due in {days} day(s). Due: {due_date}. Upcoming — monitor schedule.",
}

# Email zones: only overdue, due_7, due_30 trigger email logging
EMAIL_ZONES = {"overdue", "due_7", "due_30"}


# ── Email Stub (log-only) ───────────────────────────────────────────────────

def _log_email(zone: str, equipment_tag: str, inspector_email: str | None, supervisor_email: str | None, days: int):
    """Log email intent. TODO: uncomment Resend call when API key available."""
    if zone in ("overdue", "due_7", "due_30"):
        if inspector_email:
            logger.info("EMAIL: inspector %s — %s %s (%d days)", inspector_email, equipment_tag, zone, days)
        if supervisor_email and zone == "overdue":
            logger.info("EMAIL: supervisor %s — %s overdue (%d days)", supervisor_email, equipment_tag, days)
        if not inspector_email and not supervisor_email:
            logger.info("EMAIL: no assignment for %s — %s (%d days)", equipment_tag, zone, days)
    # due_60, due_90: in-app only, no email


# ── Core: Check & Create Notifications ──────────────────────────────────────

def check_and_create_notifications(company_id: str) -> int:
    """
    Scan all active inspection_plans for a company,
    create due-date notifications. Deduped by
    (company_id, related_id, type, created_at date).
    Returns count of new notifications created.
    """
    db = get_db()
    created = 0

    # Fetch plans: is_active=True, final_due_date NOT NULL
    plans_result = (
        db.table("inspection_plans")
        .select("id, equipment_id, final_due_date, inspection_type")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .not_.is_("final_due_date", "null")
        .execute()
    )
    plans = plans_result.data or []

    if not plans:
        logger.info("No active plans with due dates for company %s", company_id)
        return 0

    # Pre-fetch equipment tags for title generation
    equipment_ids = list({p["equipment_id"] for p in plans if p.get("equipment_id")})
    equip_tags: dict[str, str] = {}
    if equipment_ids:
        eq_result = (
            db.table("equipment")
            .select("id, tag, type")
            .in_("id", equipment_ids)
            .execute()
        )
        for eq in (eq_result.data or []):
            equip_tags[eq["id"]] = eq.get("tag") or eq.get("type") or "Unknown"

    # Date range for dedup (today UTC)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    tomorrow_start = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()

    # Find a supervisor/super_admin user for user_id (DB has NOT NULL constraint)
    # Notifications are still broadcast — GET /notifications filters by company_id
    admin_user = (
        db.table("app_users")
        .select("id")
        .eq("company_id", company_id)
        .in_("role", ["supervisor", "super_admin"])
        .limit(1)
        .execute()
    )
    default_user_id = (admin_user.data or [{}])[0].get("id")
    if not default_user_id:
        # Fallback: any user in company
        any_user = (
            db.table("app_users")
            .select("id")
            .eq("company_id", company_id)
            .limit(1)
            .execute()
        )
        default_user_id = (any_user.data or [{}])[0].get("id")

    if not default_user_id:
        logger.warning("No users found for company %s, skipping notifications", company_id)
        return 0

    for plan in plans:
        zone = get_due_zone(plan.get("final_due_date"))
        if zone is None:
            continue

        # Dedup: same plan + same zone + same date
        existing = (
            db.table("notifications")
            .select("id")
            .eq("company_id", company_id)
            .eq("related_id", plan["id"])
            .eq("type", zone)
            .gte("created_at", today_start)
            .lt("created_at", tomorrow_start)
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        # Calculate days for message
        due_date_str = plan.get("final_due_date")
        due = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")) if isinstance(due_date_str, str) else due_date_str
        due_date = due.date() if hasattr(due, "date") else due
        today = now.date()
        days = (due_date - today).days

        equipment_tag = equip_tags.get(plan.get("equipment_id"), "Unknown")
        title = ZONE_TITLES[zone].format(tag=equipment_tag)
        message = ZONE_MESSAGES[zone].format(days=abs(days), due_date=str(due_date))

        # Insert notification
        db.table("notifications").insert({
            "company_id": company_id,
            "user_id": default_user_id,
            "type": zone,
            "related_id": plan["id"],
            "title": title,
            "message": message,
            "is_read": False,
        }).execute()
        created += 1

        # Email logging
        _log_email_for_plan(db, company_id, plan, zone, equipment_tag, days)

    logger.info("Created %d notifications for company %s", created, company_id)
    return created


def _log_email_for_plan(db, company_id: str, plan: dict, zone: str, equipment_tag: str, days: int):
    """Look up inspector emails via plan_assignments and log email intent."""
    inspector_email = None
    supervisor_email = None

    try:
        # Get assigned inspectors for this plan
        assignments = (
            db.table("plan_assignments")
            .select("inspector_id, role_in_plan")
            .eq("plan_id", plan["id"])
            .execute()
        )
        if assignments.data:
            inspector_ids = [a["inspector_id"] for a in assignments.data if a.get("inspector_id")]
            if inspector_ids:
                users_result = (
                    db.table("app_users")
                    .select("id, email, role")
                    .in_("id", inspector_ids)
                    .execute()
                )
                for u in (users_result.data or []):
                    if u.get("role") == "inspector":
                        inspector_email = u.get("email")
                    elif u.get("role") in ("supervisor", "super_admin"):
                        supervisor_email = u.get("email")
    except Exception as e:
        logger.warning("Email lookup failed for plan %s: %s", plan["id"], e)

    _log_email(zone, equipment_tag, inspector_email, supervisor_email, days)


# ── Run for All Companies ───────────────────────────────────────────────────

def run_for_all_companies() -> dict:
    """
    Iterate all companies and create notifications.
    Called by POST /notifications/run (cron endpoint).
    Returns summary: {companies_processed, notifications_created}.
    """
    db = get_db()
    companies = db.table("companies").select("id").execute()
    total_created = 0
    processed = 0

    for comp in (companies.data or []):
        try:
            count = check_and_create_notifications(comp["id"])
            total_created += count
            processed += 1
        except Exception as e:
            logger.error("Notification error for company %s: %s", comp["id"], e)

    return {
        "companies_processed": processed,
        "notifications_created": total_created,
    }
