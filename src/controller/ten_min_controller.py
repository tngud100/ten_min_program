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
from src.utils.api import Api
from src.utils.remote_controller import RemoteController
from src.utils.error_handler import ErrorHandler
from src.dao.remote_pcs_dao import RemoteDao
from src.dao.auto_ten_min_dao import AutoTenMinDao
from src.dao.deanak_dao import DeanakDao
from src.utils.image_matcher import ImageMatcher
from src.utils.capture import CaptureUtil
from src.utils.input_controller import InputController
from src.utils.error_handler import CantFindRemoteProgram, TenMinError, ErrorHandler, CheckTimerError, CantFindTenMinDataError, OTPError, NoWorkerError, CantFindPcNumError, OTPTimeoutError, NoDetectionError, OTPOverTimeDetectError, TemplateEmptyError, ControllerError

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
api = Api()

# 서비스 객체들 초기화
template_service = TemplateService(image_matcher)
otp_service = OTPService(image_matcher, capture, input_controller, template_service)
ten_min_timer_service = TenMinTimerService(remote, error_handler, remote_pcs_dao, auto_ten_min_dao, deanak_dao, input_controller, state, api, image_matcher, capture, template_service)
auto_ten_min = AutoTenMin(image_matcher, input_controller, template_service, capture, state, remote_pcs_dao, remote, auto_ten_min_dao, api)
do_service = DoService(remote, error_handler, state, deanak_dao, remote_pcs_dao, otp_service, auto_ten_min, ten_min_timer_service, auto_ten_min_dao, api)

async def do_task(request, ten_min_info:dict=None):
    """태스크 실행"""
    print(f"태스크 실행: request={request}, ten_min_state={ten_min_info['ten_min_state']}")

    try:
        server_id = await unique_id.read_unique_id()
        worker_id = ten_min_info['worker_id']
        context = {"deanak_id": ten_min_info['deanak_id'], "worker_id": ten_min_info['worker_id']}
            
        if request == "otp_check":
            # 작업 상태 업데이트
            async with get_db_context() as db:
                await remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "working")
            await api.send_start(ten_min_info['deanak_id'])

            await asyncio.sleep(15)
            if not await do_otp(ten_min_info, server_id):
                return False
            print("otp 인식 완료, 5초 뒤 10분 접속 작업 시작")
            await do_task("ten_min_start", ten_min_info)

        if request == "ten_min_start":
            # 먼저 대기 중인 10분 접속 데이터 처리
            # await ten_min_timer_service.process_waiting_tasks()
            # 작업 상태 업데이트는 대기 중인 데이터 처리 후에 수행
            if not ten_min_info['otp']:
                async with get_db_context() as db:
                    await remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "working")
                await api.send_start(ten_min_info['deanak_id'])

            await asyncio.sleep(5)
            if not await do_ten_min(ten_min_info, server_id):
                return False

        return await pending_task()

    except TemplateEmptyError as e:
        update_error_status(server_id, e, context, error_handler.TEMPLATE_EMPTY_ERROR)
        return False
    except NoWorkerError as e:
        update_error_status(server_id, e, context, error_handler.NO_WORKER_ERROR)
        return False
    except CantFindPcNumError as e:
        update_error_status(server_id, e, context, error_handler.CANT_FIND_PC_NUM_ERROR)
        return False
    except CantFindRemoteProgram as e:
        update_error_status(server_id, e, context, error_handler.CANT_FIND_REMOTE_PROGRAM)
        return False
    
    except Exception as e:
        raise ControllerError(f"do_task 작업 실패 - 알수 없는 오류")

async def pending_task():
    """대기 중인 요청 처리"""
    try:
        while not state.pending_services.empty():
            next_request = await state.pending_services.get()
            print(f"대기 중이던 요청 처리 시작: worker_id={next_request['worker_id']}")
            await do_task(
                next_request['request'],
                next_request['ten_min_info']
            )
    except Exception as e:
        error_handler.handle_error(e)
        print(f"대기 중인 요청 처리 중 오류 발생: {e}")

async def do_otp(ten_min_info, server_id):
    context = {"deanak_id": ten_min_info['deanak_id'], "worker_id": ten_min_info['worker_id']}
    try:
        return await do_service.check_otp(ten_min_info)
        
    except OTPOverTimeDetectError as e:
        await update_error_status(server_id, e, context, error_handler.OTP_OVER_TIME_DETECT)
        return False
    except OTPTimeoutError as e:
        await update_error_status(server_id, e, context, error_handler.OTP_TIME_OUT)
        return False
    except NoDetectionError as e:
        await update_error_status(server_id, e, context, error_handler.NO_DETECT_OTP_SCENE)
        return False
    except OTPError as e:
        await update_error_status(server_id, e, context, error_handler.OTP_ERROR)
        return False
    except (TemplateEmptyError, NoWorkerError, CantFindPcNumError, CantFindRemoteProgram) as e:
        raise
    except Exception as e:
        raise ControllerError(f"OTP 작업 중 오류 - do_task")

async def do_ten_min(ten_min_info, server_id):
    context = {"deanak_id": ten_min_info['deanak_id'], "worker_id": ten_min_info['worker_id']}
    try:
        return await do_service.execute_ten_min(ten_min_info)
        
    except CantFindTenMinDataError as e:
        await update_error_status(server_id, e, context, error_handler.CANT_FIND_TEN_MIN_DATA)
        return False
    except CheckTimerError as e:
        await update_error_status(server_id, e, context, error_handler.CHECK_TIMER_ERROR)
        return False
    except (TenMinError, ValueError) as e:
        await update_error_status(server_id, e, context, error_handler.TEN_MIN_ERROR)
        return False
    except (TemplateEmptyError, NoWorkerError, CantFindPcNumError, CantFindRemoteProgram) as e:
        raise
    except Exception as e:
        raise ControllerError(f"10분 작업 중 오류 - do_task")

async def update_error_status(server_id, e, context, ErrorMessage):
    """에러 처리"""
    async with get_db_context() as db:
        await remote_pcs_dao.update_tasks_request(db, server_id, context['worker_id'], "stopped")
    error_handler.handle_error(e, context=context, critical=True, user_message=ErrorMessage)

async def stop_ten_min():
    """태스크 중지"""
    return await do_service.stop_ten_min()
