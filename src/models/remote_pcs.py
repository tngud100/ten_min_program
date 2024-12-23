from sqlalchemy import Column, String, Integer, DateTime
from database import Base
from datetime import datetime

class RemotePcs(Base):
    __tablename__ = 'remote_pcs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(45), nullable=False)
    service = Column(String(255), nullable=False, default="일반대낙")
    worker_id = Column(String(255), nullable=True)
    state = Column(String(50), nullable=False)
    server_online_time = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"RemotePcs(server_id={self.server_id})"
