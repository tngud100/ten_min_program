import ctypes
import os
from dotenv import load_dotenv
import asyncio
import warnings
from src import state
from src.binlog.monitor import monitor_binlog
from src.controller.ten_min_controller import stop_ten_min
from database import AsyncSessionLocal, async_engine
from src.dao.remote_pcs_dao import RemoteDao
from database import get_db_context
from src.utils.api import Api
from src.utils.error_handler import ErrorHandler
from src.logging import LogWindow
from src.logging import PrintLogger

# 전역 변수로 이벤트 루프 참조 저장
loop = None
error_handler = ErrorHandler()
api = Api()

def setup_signal_handlers():
    """시그널 핸들러 설정"""
    # 콘솔 창 닫기 버튼(X) 비활성화
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        ctypes.windll.user32.GetSystemMenu(hwnd, True)

async def setup_logging():
    """로깅 설정"""
    try:
        # GUI 로그 윈도우 초기화
        LogWindow.initialize_app()
        log_window = LogWindow.get_instance()
        
        # 로거 초기화
        PrintLogger.initialize()
        
        # GUI 종료 시 프로그램 종료 처리 설정
        async def on_close(*args):
            print("\nGUI 종료로 인한 프로그램 종료")
            # Qt 이벤트 루프 종료
            await cleanup_resources(is_shutting_down=True)
            os._exit(0)
            
        # GUI 이벤트 처리를 위한 태스크 생성
        async def process_gui_events():
            while True:
                await asyncio.sleep(0.1)  # GUI 이벤트 처리를 위한 지연
                LogWindow._app.processEvents()
        
        LogWindow.set_close_callback(on_close)
        
        # GUI 이벤트 처리 태스크 생성
        asyncio.create_task(process_gui_events())
        
        return log_window
        
    except Exception as e:
        error_handler.handle_error(e)
        raise

async def cleanup_resources(is_shutting_down=False):
    """리소스 정리 함수"""
    unique_id_value = None
    unique_id_instance = state.unique_id()
    try:
        if not os.path.exists(unique_id_instance.file_path):
            return
            
        # unique_id 확인
        unique_id_value = await unique_id_instance.read_unique_id()

        # DB 정리
        async with get_db_context() as db:
            await RemoteDao.delete_remote_pc_by_server_id(db, unique_id_value)
            print("DB에서 원격 PC 정보 제거 완료")
        if async_engine:
            await async_engine.dispose()
            print("DB 엔진 정리 완료")

        # 실행 중인 태스크 정리
        if unique_id_value and state.is_running:
            await stop_ten_min()
        # 실행 중인 모든 태스크 정리 (monitoring_task 포함)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        print("실행 중인 태스크 정리 완료")
        
        # server에 종료 API 호출
        await shutdown(unique_id_value)

        # 서버 ID 파일 정리
        await unique_id_instance.delete_unique_id()
        print("unique_id.txt 파일 삭제 완료")

        # GUI 리소스 정리
        if is_shutting_down:
            LogWindow._is_shutting_down = True
            PrintLogger.cleanup()
            if LogWindow._instance:
                LogWindow._instance.close()
            print("GUI 리소스 정리 완료")
            if is_shutting_down and LogWindow._app:
                LogWindow._app.quit()
                print("Qt 애플리케이션 종료 완료")

        print("모든 리소스 정리 완료")
                    
    except Exception as e:
        error_handler.handle_error(e)
    

async def startup():
    """시작 시 초기화"""
    # 로깅 설정 먼저 초기화
    await setup_logging()

    unique_id_instance = state.unique_id()
    unique_id_value = await unique_id_instance.generate_unique_id()
    print(f"고유 ID: {unique_id_value}")
    
    # DB에 server_id 등록
    async with AsyncSessionLocal() as db:
        await RemoteDao.insert_remote_pc_server_id(db, unique_id_value)
        # for i in range(5):
    await api.send_login(unique_id_value)
    
    return unique_id_value
    

async def shutdown(unique_id_value):
    """최종 종료"""
    print(f"Server ID: {unique_id_value}")  
    if unique_id_value:
        await api.send_disconnect(unique_id_value)

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
    setup_signal_handlers()
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cleanup_resources())
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
    finally:
        loop.run_until_complete(cleanup_resources(is_shutting_down=True))
        loop.close()