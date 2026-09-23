import hashlib
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditLog

def compute_hash(data: dict | None) -> str | None:
    if data is None:
        return None
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

def append_audit_log(
    session: AsyncSession,
    encounter_id: str,
    actor: str,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
    field_path: str | None = None
):
    """Writes an immutable audit log row with before/after diffs."""
    before_hash = compute_hash(before)
    after_hash = compute_hash(after)
    
    diff_jsonb = None
    if before is not None or after is not None:
        diff_jsonb = {"before": before, "after": after}
        
    audit = AuditLog(
        encounter_id=uuid.UUID(encounter_id) if isinstance(encounter_id, str) else encounter_id,
        actor=actor,
        action=action,
        field_path=field_path,
        before_hash=before_hash,
        after_hash=after_hash,
        diff_jsonb=diff_jsonb
    )
    session.add(audit)
