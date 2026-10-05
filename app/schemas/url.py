from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class URLCreate(BaseModel):
    original_url: str

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        if not (v.startswith("http://") or v.startswith("https://")):
            # Auto-prefix http/https if missing protocol
            v = "https://" + v
        return v


class URLResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    short_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_links: int
    total_clicks: int
    active_links: int
