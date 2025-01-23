from ast import stmt
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
            raise

    @staticmethod
    async def get_otp_pass_by_deanak_id(db, deanak_id):
        try:
            stmt = select(DeanakModel.otp_pass).where(DeanakModel.id == deanak_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"otp_pass 구하기 중 오류 발생: {e}")
            raise

    @staticmethod
    async def update_otp_pass(db, deanak_id, otp_pass):
        try:
            stmt = update(DeanakModel).where(DeanakModel.id == deanak_id).values(otp_pass=otp_pass)
            await db.execute(stmt)
            await db.commit()
            return True
        except Exception as e:
            print(f"otp_pass 업데이트 중 오류 발생: {e}")
            raise
