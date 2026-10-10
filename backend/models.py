from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from zoneinfo import ZoneInfo


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Model):
    workspace: str = Field(default='madar', max_length=80)
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class LeadInput(Model):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(default='', max_length=30)
    email: str = Field(default='', max_length=200)
    source: Literal['website', 'whatsapp', 'telegram', 'facebook', 'instagram', 'email', 'crm'] = 'website'
    external_id: str = Field(default='', max_length=200)
    budget: float = Field(default=0, ge=0, le=1e12)
    location: str = Field(default='', max_length=150)
    property_type: Literal['', 'Apartment', 'Villa', 'Office', 'Land'] = ''
    intent: Literal['buy', 'rent'] = 'buy'
    bedrooms: int = Field(default=0, ge=0, le=50)
    min_size: float = Field(default=0, ge=0, le=1000000)
    amenities: list[str] = Field(default_factory=list, max_length=30)
    consent: bool = False


class LeadPatch(Model):
    stage: str | None = Field(default=None, max_length=60)
    assigned_to: str | None = None
    budget: float | None = Field(default=None, ge=0, le=1e12)
    location: str | None = Field(default=None, max_length=150)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    consent: bool | None = None
    opted_out: bool | None = None


class Chat(Model):
    text: str = Field(min_length=1, max_length=4000)


class PublicChat(Model):
    tenant_slug: str = Field(max_length=80)
    session: str = Field(default='', max_length=100)
    name: str = Field(default='Website visitor', max_length=160)
    text: str = Field(min_length=1, max_length=4000)
    consent: bool = False


class PropertyInput(Model):
    title: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=150)
    property_type: Literal['Apartment', 'Villa', 'Office', 'Land'] = 'Apartment'
    intent: Literal['buy', 'rent'] = 'buy'
    price: float = Field(gt=0, le=1e12)
    size: float = Field(gt=0, le=1000000)
    bedrooms: int = Field(default=0, ge=0, le=50)
    amenities: list[str] = Field(default_factory=list, max_length=30)
    description: str = Field(default='', max_length=4000)
    image: str = Field(default='', max_length=1000)
    status: Literal['Available', 'Reserved', 'Sold', 'Rented'] = 'Available'


class Booking(Model):
    lead_id: str
    property_id: str
    agent_id: str
    start_at: str
    notes: str = Field(default='', max_length=1000)


class TaskInput(Model):
    lead_id: str
    title: str = Field(min_length=1, max_length=200)
    due_at: str


class DealInput(Model):
    lead_id: str
    property_id: str | None = None
    amount: float = Field(ge=0, le=1e12)
    commission: float = Field(default=0, ge=0, le=1e12)
    status: Literal['Open', 'Won', 'Lost'] = 'Open'
    lost_reason: str = Field(default='', max_length=1000)


class UserInput(Model):
    email: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=160)
    role: Literal['admin', 'agent'] = 'agent'
    password: str = Field(min_length=12, max_length=200)


class WorkspaceInput(Model):
    slug: str = Field(pattern=r'^[a-z][a-z0-9-]{2,60}$')
    company_name: str = Field(min_length=1, max_length=160)
    owner_name: str = Field(min_length=1, max_length=160)
    owner_email: str = Field(min_length=3, max_length=200)
    owner_password: str = Field(min_length=12, max_length=200)


class PasswordInput(Model):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class SettingsInput(Model):
    company_name: str = Field(min_length=1, max_length=160)
    brand_color: str = '#D8BE83'
    logo_url: str = Field(default='', max_length=1000)
    currency: Literal['EGP', 'AED', 'SAR', 'USD'] = 'EGP'
    language: Literal['en', 'ar'] = 'en'
    timezone: str = 'Africa/Cairo'
    business_start: int = Field(default=9, ge=0, le=23)
    business_end: int = Field(default=18, ge=1, le=24)
    stages: list[str] = Field(default=['New', 'Qualified', 'Viewing', 'Negotiation', 'Won', 'Lost'], min_length=6, max_length=20)
    assistant_name: str = Field(default='Madar', max_length=80)
    personality: str = Field(default='Helpful, concise, honest property adviser', max_length=1000)
    followup_hours: int = Field(default=24, ge=1, le=720)
    company_details: str = Field(default='', max_length=3000)
    onboarding_complete: bool = False

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except Exception:
            raise ValueError('Unknown timezone')
        return value

    @field_validator('stages')
    @classmethod
    def valid_stages(cls, value):
        if not {'New', 'Qualified', 'Viewing', 'Negotiation', 'Won', 'Lost'}.issubset(value) or len(set(value)) != len(value):
            raise ValueError('Keep core stages and use unique names')
        return value
