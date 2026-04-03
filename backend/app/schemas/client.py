from pydantic import BaseModel


class ClientSummary(BaseModel):
    name: str
    dob: str | None = None
    age: int | None = None
    blood_type: str | None = None
    conditions: list[str] = []


class NgAction(BaseModel):
    action: str
    reason: str | None = None
    risk_level: str = "Discomfort"  # LifeThreatening | Panic | Discomfort


class CarePreference(BaseModel):
    category: str
    instruction: str
    priority: str | None = None


class KeyPerson(BaseModel):
    name: str
    relationship: str | None = None
    phone: str | None = None
    rank: int | None = None


class EmergencyInfo(BaseModel):
    client_name: str
    ng_actions: list[NgAction] = []
    care_preferences: list[CarePreference] = []
    key_persons: list[KeyPerson] = []
    hospital: dict | None = None
    guardian: dict | None = None


class SupportLogEntry(BaseModel):
    date: str | None = None
    situation: str | None = None
    action: str | None = None
    effectiveness: str | None = None
    note: str | None = None
    supporter_name: str | None = None


class ClientDetail(BaseModel):
    name: str
    dob: str | None = None
    age: int | None = None
    blood_type: str | None = None
    conditions: list[dict] = []
    ng_actions: list[NgAction] = []
    care_preferences: list[CarePreference] = []
    key_persons: list[KeyPerson] = []
    certificates: list[dict] = []
    hospital: dict | None = None
    guardian: dict | None = None


class DashboardStats(BaseModel):
    client_count: int = 0
    log_count_this_month: int = 0
    renewal_alerts: int = 0


class RenewalAlert(BaseModel):
    client_name: str
    certificate_type: str
    next_renewal_date: str
    days_remaining: int


class ActivityEntry(BaseModel):
    date: str
    client_name: str
    action: str
    summary: str
