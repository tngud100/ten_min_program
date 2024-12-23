from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from database import Base
from datetime import datetime
from src.models.service_state import ServiceState
from src import state as global_state

class TenMinModel(Base):
    __tablename__ = 'auto_ten_min'
    
    deanak_id = Column(Integer, primary_key=True)
    server_id = Column(Integer, nullable=False)
    pc_num = Column(Integer, nullable=False)
    state = Column(SQLEnum(ServiceState), nullable=False, default=ServiceState.READY)
    start_waiting_time = Column(DateTime, nullable=False, default=datetime.now)
    end_waiting_time = Column(DateTime, nullable=True)

    @property
    def is_expired(self) -> bool:
        """10분 대기 시간이 만료되었는지 확인"""
        if not self.start_waiting_time:
            return False
        time_diff = (datetime.now() - self.start_waiting_time).total_seconds()
        return time_diff > global_state.SERVICE_TIMER  # 10분

    def __repr__(self):
        return f"TenMinModel(deanak_id={self.deanak_id}, server_id={self.server_id}, pc_num={self.pc_num}, state={self.state})"
