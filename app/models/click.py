from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"), nullable=False, index=True)
    clicked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Relationships
    url = relationship("URL", back_populates="clicks")
