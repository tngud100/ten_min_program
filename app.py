import os
from dotenv import load_dotenv
import asyncio
import warnings
from src import state
from src.binlog.monitor import monitor_binlog
from config.settings import DB_CONFIG
from src.controller.ten_min_controller import stop_ten_min
from database import AsyncSessionLocal, async_engine
from src.dao.remote_pcs_dao import RemoteDao
from database import get_db_context
from src.utils.error_handler import ErrorHandler

# 전역 변수로 이벤트 루프 참조 저장
loop = None
error_handler = ErrorHandler()

async def cleanup_resources():
    """리소스 정리 함수"""
    try:
        # monitoring_task 정리
        if state.monitoring_task and not state.monitoring_task.done():
            state.monitoring_task.cancel()
            try:
                await state.monitoring_task
            except asyncio.CancelledError:
                print("모니터링 태스크가 성공적으로 취소되었습니다")

        print("리소스 정리 완료")

        try:
            unique_id_instance = state.unique_id()
            if os.path.exists(unique_id_instance.file_path):
                unique_id_value = await unique_id_instance.read_unique_id()
                if unique_id_value:  # unique_id가 있을 때만 정리 작업 수행
                    await stop_ten_min()
                    print("ten_min 태스크 정리 완료")
                    # DB에서 server_id 제거
                    async with get_db_context() as db:
                        if await RemoteDao.delete_remote_pc_by_server_id(db, unique_id_value):
                            print("DB에서 원격 PC 정보 제거 완료")

                    await unique_id_instance.delete_unique_id()
                    
                    if async_engine:
                        await async_engine.dispose()
                        print("DB 엔진 정리 완료")
                    
        except Exception as e:
            error_handler.handle_error(e, context={'unique_id_value': unique_id_value})
    except Exception as e:
        print(f"리소스 정리 중 오류 발생: {e}")
    

async def startup():
    """시작 시 초기화"""
    unique_id_instance = state.unique_id()
    unique_id_value = await unique_id_instance.generate_unique_id()
    print(f"고유 ID: {unique_id_value}")
    
    # DB에 server_id 등록
    async with AsyncSessionLocal() as db:
        for i in range(5):
            await RemoteDao.insert_remote_pc_server_id(db, unique_id_value)
    
    return unique_id_value
    
async def main():
    """메인 애플리케이션 로직"""
    try:
        unique_id_value = await startup()
        await monitor_binlog(unique_id_value)
    except Exception as e:
        print(f"애플리케이션 오류: {e}")

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    load_dotenv()
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cleanup_resources())
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
    finally:
        loop.run_until_complete(cleanup_resources())
        loop.close()