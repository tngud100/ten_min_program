from src.models.remote_pcs import RemotePcs
from src.models.remote_worker_pc import RemoteWorkerPcs
from sqlalchemy import select, delete, update, and_
from database import AsyncSessionLocal
import asyncio

class RemoteDao:
    @staticmethod
    async def insert_remote_pc_server_id(db, server_id):
        """원격 PC 서버 ID를 데이터베이스에 삽입"""
        try:
            remote_pc = RemotePcs(
                server_id=server_id,
                service="10분접속",
                state="None"
            )
            db.add(remote_pc)
            await db.commit()
            return True
        except Exception as e:
            print(f"원격 PC 서버 ID 삽입 중 오류 발생: {e}")
            raise

    @staticmethod
    async def delete_remote_pc_by_server_id(db, server_id):
        """서버 ID로 원격 PC 정보 삭제"""
        try:
            stmt = delete(RemotePcs).where(RemotePcs.server_id == server_id)
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            print(f"원격 PC 서버 ID 삭제 중 오류 발생: {e}")
            raise

    @staticmethod
    async def get_pc_num_by_worker_id(db, worker_id):
        """작업자 ID로 PC 번호 조회
        
        Args:
            db: 데이터베이스 세션
            worker_id (str): 작업자 ID
            
        Returns:
            int: PC 번호. 없으면 None
        """
        try:
            stmt = select(RemoteWorkerPcs).where(RemoteWorkerPcs.worker_id == worker_id)
            result = await db.execute(stmt)
            remote_pc = result.scalar_one_or_none()
            return remote_pc.pc_num if remote_pc else None
        except Exception as e:
            print(f"원격 PC 번호 조회 중 오류 발생: {e}")
            return None
        
    @staticmethod
    async def get_remote_pc_by_server_id_and_worker_id(db, server_id, worker_id):
        """서버 ID로 PC 상태 조회"""
        try:
            stmt = select(RemotePcs).where(
                and_(
                    RemotePcs.server_id == server_id,
                    RemotePcs.worker_id == worker_id
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none() if result else None
        except Exception as e:
            print(f"PC 상태 조회 중 오류 발생: {e}")
            return None

    @staticmethod 
    async def update_tasks_request(db, server_id, worker_id, request):
        """작업 요청 상태 업데이트"""
        try:
            if worker_id is None:
                return False

            # 업데이트 수행
            stmt = update(RemotePcs).where(
                and_(
                    RemotePcs.server_id == server_id,
                    RemotePcs.worker_id == worker_id
                )
            ).values(state=request)
            await db.execute(stmt)
            await db.commit()

            return True
        except Exception as e:
            print(f"작업 요청 상태 업데이트 중 오류 발생: {e}")
            return False

    @staticmethod
    async def get_working_count_by_server_id(db, server_id):
        """서버 ID에 대한 현재 작업 중인 PC 수 조회
        
        Args:
            db: 데이터베이스 세션
            server_id (str): 서버 ID
            
        Returns:
            int: 작업 중인 PC 수
        """
        try:
            stmt = select(RemotePcs).where(
                and_(
                    RemotePcs.server_id == server_id,
                    RemotePcs.state == 'working'
                )
            )
            result = await db.execute(stmt)
            return len(result.scalars().all())
        except Exception as e:
            print(f"작업 중인 PC 수 조회 중 오류 발생: {e}")