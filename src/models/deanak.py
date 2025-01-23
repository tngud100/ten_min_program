

from database import Base
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime

class DeanakModel(Base):
    __tablename__ = 'daenak'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String(255), nullable=False)
    worker_id = Column(String(255), nullable=True)
    coupon_count = Column(Integer, nullable=False, default=0)
    otp = Column(String(255), nullable=False)
    state = Column(String(50), nullable=False)
    otp_pass = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"Deanak(deanak_id={self.id})"
