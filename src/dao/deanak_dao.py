from src.models.deanak import DeanakModel
from sqlalchemy import update, and_, select

class DeanakDao:
    @staticmethod
    async def get_worker_id_by_deanak_id(db, deanak_id):
        try:
            stmt = select(DeanakModel.worker_id).where(DeanakModel.id == deanak_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"worker_id 구하기 중 오류 발생: {e}")
            return None