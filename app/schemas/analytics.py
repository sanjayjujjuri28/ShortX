from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ClickTimelinePoint(BaseModel):
    date: str
    clicks: int


class URLAnalyticsResponse(BaseModel):
    id: int
    short_code: str
    short_url: str
    original_url: str
    total_clicks: int
    created_at: datetime
    last_click_at: Optional[datetime] = None
    clicks_timeline: List[ClickTimelinePoint] = []

    model_config = ConfigDict(from_attributes=True)
