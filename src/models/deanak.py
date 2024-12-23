

from database import Base
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime

class DeanakModel(Base):
    __tablename__ = 'deanak'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(45), nullable=False)
    service = Column(String(255), nullable=False)
    worker_id = Column(String(255), nullable=True)
    state = Column(String(50), nullable=False)
    server_online_time = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"Deanak(server_id={self.server_id})"
