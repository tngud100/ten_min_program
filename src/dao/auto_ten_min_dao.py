from src.models.auto_ten_min import TenMinModel
from sqlalchemy import or_, update, and_, select
from datetime import datetime, timedelta
from src.models.service_state import ServiceState
from src import state as global_state

class AutoTenMinDao:
    @staticmethod
    async def insert_ten_min_start(db, deanak_id=None, server_id=None, pc_num=None):
        try:
            stmt = TenMinModel(
                deanak_id=deanak_id,
                server_id=server_id,
                pc_num=pc_num,
                state=ServiceState.WAITING
            )
            db.add(stmt)
            await db.commit()
            return True
        except Exception as e:
            print(f"auto_ten_min데이터베이스에 insert 중 오류 발생: {e}")
            raise

        
    @staticmethod
    async def find_auto_ten_min(db, deanak_id, server_id):
        try:
            stmt = select(TenMinModel).where(
                and_(
                    TenMinModel.deanak_id == deanak_id,
                    TenMinModel.server_id == server_id,
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"auto_ten_min데이터베이스에 find 중 오류 발생: {e}")
            raise


    @staticmethod
    async def waiting_ten_min(db):
        """대기 중인 10분 접속 데이터 조회"""
        try:
            stmt = select(TenMinModel).where(
                or_(
                    TenMinModel.state == ServiceState.WAITING,
                     TenMinModel.state == ServiceState.TIMEOUT
                     )
                ).order_by(
                    TenMinModel.start_waiting_time.asc()
                )
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            print(f"대기 중인 10분접속 데이터 조회 중 오류 발생: {e}")
            raise


    @staticmethod
    async def get_waiting_queue_by_server_id(db, server_id):
        """대기 큐를 시간순으로 조회
        
        Args:
            db: 데이터베이스 세션
            server_id (str): 서버 ID
            
        Returns:
            List[TenMinModel]: 대기 중인 PC 목록
        """
        try:
            stmt = select(TenMinModel).where(
                and_(
                    TenMinModel.server_id == server_id,
                    TenMinModel.state == ServiceState.TIMEOUT
                )
            ).order_by(TenMinModel.start_waiting_time.asc())
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            print(f"대기 큐 조회 중 오류 발생: {e}")
            raise

    @staticmethod
    async def update_ten_min_state(db, deanak_id: int, server_id: str, state: ServiceState, end_waiting_time: datetime = None):
        """서비스 상태 업데이트
        
        Args:
            db: 데이터베이스 세션
            deanak_id (int): 대낙 ID
            server_id (str): 서버 ID
            state (ServiceState): 새로운 상태
        """
        try:
            stmt = update(TenMinModel).where(
                and_(
                    TenMinModel.deanak_id == deanak_id,
                    TenMinModel.server_id == server_id,
                )
            ).values(
                state=state,
                end_waiting_time=end_waiting_time if state == ServiceState.TERMINATED else None
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            print(f"서비스 상태 업데이트 중 오류 발생: {e}")
            raise

    @staticmethod
    async def get_expired_services(db):
        """만료된 서비스 목록 조회"""
        try:
            # 현재 시간과 만료 기준 시간 계산
            current_time = datetime.now()
            
            # WAITING 상태인 서비스들 조회
            stmt = select(TenMinModel).where(
                TenMinModel.state == ServiceState.WAITING
            )
            result = await db.execute(stmt)
            waiting_services = result.scalars().all()
            
            # 만료된 서비스 필터링
            expired_services = []
            for service in waiting_services:
                time_diff = (current_time - service.start_waiting_time).total_seconds()
                print(f"\n시간 체크 - deanak_id: {service.deanak_id}")
                # print(f"시작 시간: {service.start_waiting_time}")
                # print(f"현재 시간: {current_time}")
                print(f"경과 시간: {time_diff}초")
                # print(f"설정된 타이머: {global_state.SERVICE_TIMER}초")
                
                # 1초의 오차 범위를 허용
                if time_diff >= (global_state.SERVICE_TIMER - 1):
                    print(f"==> 시간 초과됨!")
                    expired_services.append(service)
                else:
                    print(f"==> 아직 {global_state.SERVICE_TIMER - time_diff:.1f}초 남음")
            
            return expired_services
            
        except Exception as e:
            print(f"만료된 서비스 조회 중 오류 발생: {e}")
            raise