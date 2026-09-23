import enum
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, BigInteger, text, JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

# Dialect-agnostic types
DbUUID = Uuid(as_uuid=True)
DbJSONB = JSON().with_variant(JSONB, "postgresql")
DbBigInteger = Integer().with_variant(BigInteger, "postgresql")

Base = declarative_base()

class EncounterState(str, enum.Enum):
    created = 'created'
    consented = 'consented'
    recording = 'recording'
    transcribing = 'transcribing'
    drafting = 'drafting'
    ready = 'ready'
    signed = 'signed'
    degraded = 'degraded'
    cancelled = 'cancelled'

class ConsentState(str, enum.Enum):
    pending = 'pending'
    granted = 'granted'
    declined = 'declined'
    granted_verbal_witnessed = 'granted_verbal_witnessed'

class Encounter(Base):
    __tablename__ = 'encounters'
    
    id = Column(DbUUID, primary_key=True)
    clinician_id = Column(String, nullable=False)
    patient_ref = Column(String, nullable=False)
    consent_state = Column(String, nullable=False, default=ConsentState.pending.value)
    consent_logged_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    state = Column(String, nullable=False, default=EncounterState.created.value)
    retention_opt_in = Column(Boolean, server_default='false', nullable=False)
    degraded_reason = Column(String, nullable=True)

class NoteVersion(Base):
    __tablename__ = 'note_versions'
    
    id = Column(DbUUID, primary_key=True)
    encounter_id = Column(DbUUID, ForeignKey('encounters.id'), nullable=False)
    version = Column(Integer, nullable=False)
    source = Column(String, nullable=False) # 'ai' | 'clinician'
    content_jsonb = Column(DbJSONB, nullable=False)
    model_name = Column(String, nullable=False)
    model_hash = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(DbBigInteger, primary_key=True, autoincrement=True)
    encounter_id = Column(DbUUID, ForeignKey('encounters.id'), nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    field_path = Column(String, nullable=True)
    before_hash = Column(String, nullable=True)
    after_hash = Column(String, nullable=True)
    diff_jsonb = Column(DbJSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
