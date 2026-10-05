from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class URL(Base):
    __tablename__ = "shortx_urls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("shortx_users.id", ondelete="CASCADE"), nullable=True, index=True)
    original_url = Column(Text, nullable=False)
    short_code = Column(String(32), unique=True, index=True, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="urls")
    clicks = relationship("Click", back_populates="url", cascade="all, delete-orphan", order_by="desc(Click.clicked_at)")
