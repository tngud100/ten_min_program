import asyncio
from enum import auto
from src import state
from database import get_db_context
from src.models import deanak
from src.service import ten_min_timer_service
from src.service.ten_min_timer_service import TenMinTimerService
from src.service.do_service import DoService
from src.service.otp_service import OTPService
from src.service.template_service import TemplateService
from src.service.auto_ten_min import AutoTenMin
from src.utils.remote_controller import RemoteController
from src.utils.error_handler import ErrorHandler
from src.dao.remote_pcs_dao import RemoteDao
from src.dao.auto_ten_min_dao import AutoTenMinDao
from src.dao.deanak_dao import DeanakDao
from src.utils.image_matcher import ImageMatcher
from src.utils.capture import CaptureUtil
from src.utils.input_controller import InputController

# 공통으로 사용할 객체들 초기화
image_matcher = ImageMatcher()
capture = CaptureUtil()
input_controller = InputController()
remote = RemoteController()
error_handler = ErrorHandler()
remote_pcs_dao = RemoteDao()
auto_ten_min_dao = AutoTenMinDao()
deanak_dao = DeanakDao()
unique_id = state.unique_id()

# 서비스 객체들 초기화
template_service = TemplateService(image_matcher)
otp_service = OTPService(image_matcher, capture, input_controller, template_service)
ten_min_timer_service = TenMinTimerService(remote, error_handler, remote_pcs_dao, auto_ten_min_dao, deanak_dao, input_controller, state)
auto_ten_min = AutoTenMin(image_matcher, input_controller, template_service, capture, state, remote_pcs_dao, remote, auto_ten_min_dao)
do_service = DoService(remote, error_handler, state, remote_pcs_dao, otp_service, auto_ten_min, ten_min_timer_service, auto_ten_min_dao)

async def do_task(request, ten_min_info:dict=None):
    """태스크 실행"""
    print(f"태스크 실행: request={request}, ten_min_state={ten_min_info['ten_min_state']}")

    try:
        server_id = await unique_id.read_unique_id()
        worker_id = ten_min_info['worker_id']
            
        if request == "otp_check":
            # 작업 상태 업데이트
            async with get_db_context() as db:
                await remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "working")
            await do_service.check_otp(ten_min_info)

        if request == "ten_min_start":
            # 먼저 대기 중인 10분 접속 데이터 처리
            await ten_min_timer_service.process_waiting_tasks()

            # 작업 상태 업데이트는 대기 중인 데이터 처리 후에 수행
            async with get_db_context() as db:
                print(f"server_id={server_id}, worker_id={worker_id} state를 working으로 변경.")
                await remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "working")

            await do_service.execute_ten_min(ten_min_info)

        # 서비스 완료 후 대기 중인 요청 처리
        try:
            while not state.pending_services.empty():
                next_request = await state.pending_services.get()
                print(f"대기 중이던 요청 처리 시작: worker_id={next_request['worker_id']}")
                await do_task(
                    next_request['request'],
                    next_request['ten_min_info']
                )
        except Exception as e:
            print(f"대기 중인 요청 처리 중 오류 발생: {e}")

    except Exception as e:
        print(f"대기 중인 요청 처리 중 작업 실패: {e}")

async def stop_ten_min():
    """태스크 중지"""
    try:
        return await do_service.stop_ten_min()
    except Exception as e:
        print(f"작업 실패: {e}")