import asyncio
from src.models import deanak
from src.utils.remote_controller import RemoteController
from src.utils.error_handler import ErrorHandler, NoDetectionError, NoWorkerError, CantFindPcNumError, OTPTimeoutError
from src.dao.remote_pcs_dao import RemoteDao
from src.service.auto_ten_min import AutoTenMin
from src.dao.auto_ten_min_dao import AutoTenMinDao
from database import get_db_context
from src.service.otp_service import OTPService
from src.service.ten_min_timer_service import TenMinTimerService
from src import state
from src.models.service_state import ServiceState
from src.dao.deanak_dao import DeanakDao

class DoService:
    def __init__(self, remote: RemoteController, error_handler: ErrorHandler, state: state, deanak_dao: DeanakDao,
                 remote_pcs_dao: RemoteDao, otp_service: OTPService, auto_ten_min: AutoTenMin, ten_min_timer_service: TenMinTimerService, auto_ten_min_dao: AutoTenMinDao):
        self.remote = remote
        self.error_handler = error_handler
        self.remote_pcs_dao = remote_pcs_dao
        self.otp_service = otp_service
        self.auto_ten_min = auto_ten_min
        self.ten_min_timer_service = ten_min_timer_service
        self.auto_ten_min_dao = auto_ten_min_dao    
        self.state = state
        self.deanak_dao = deanak_dao

    async def _validate_worker(self, db, server_id, worker_id):
        """worker_id 검증 및 PC 번호 조회"""
        try:
            worker_exists = await self.remote_pcs_dao.get_remote_pc_by_server_id_and_worker_id(db, server_id, worker_id)
            if not worker_exists:
                raise NoWorkerError("해당 worker_id가 remote_pcs테이블에 존재하지 않습니다.")

            pc_num = await self.remote_pcs_dao.get_pc_num_by_worker_id(db, worker_id)
            if pc_num is None:
                raise CantFindPcNumError("PC 번호를 찾을 수 없습니다.")
            
            return pc_num
        except NoWorkerError as e:
            self.error_handler.handle_error(e, context={'worker_id': worker_id})
            return None
        except CantFindPcNumError as e:
            self.error_handler.handle_error(e, context={'worker_id': worker_id, 'server_id': server_id})
            return None

    async def check_otp(self, ten_min_info:dict=None):
        """OTP 체크 및 검증"""
        try:
            server_id = await self.state.unique_id().read_unique_id()
            worker_id = ten_min_info['worker_id']
            deanak_id = ten_min_info['deanak_id']
            already_send_otp = None
            wrong_otp_state = False
            renew_otp = False # otp번호 갱신
            
            # 타이머 설정
            start_time = asyncio.get_event_loop().time()
            max_duration = 125  # 2분
            renew_duration = 65

            async with get_db_context() as db:
                await self._validate_worker(db, server_id, worker_id)

            # 원격 연결 시작
            if not await self.remote.start_remote(worker_id=worker_id):
                return False

            # 2분 동안만 실행
            while (asyncio.get_event_loop().time() - start_time) < max_duration:
                current_time = asyncio.get_event_loop().time()
                elapsed_time = current_time - start_time
                
                # OTP 확인 통과 체크
                async with get_db_context() as db:
                    otp_pass = await self.deanak_dao.get_otp_pass_by_deanak_id(db, deanak_id)

                if otp_pass == 1:
                    break
                
                # OTP를 보내지 않았면 OTP 추출
                if already_send_otp is None:
                    # OTP 추출
                    otp_text = await self.otp_service.capture_and_extract_otp()
                    if otp_text is None:
                        print("OTP 추출 실패")
                        print("다시 인식을 시작합니다")
                    else:
                        ## 심플대낙에 otp번호 보내는 로직
                        already_send_otp = otp_text

                if already_send_otp is not None:
                    is_state_check = await self.otp_service.pass_or_wrong_otp_detect() # 0이면 이상 없음, 1이면 통과, -1이면 틀림

                # 통과로 state업데이트
                if is_state_check == 1:
                    async with get_db_context() as db:
                        await self.deanak_dao.update_otp_pass(db, deanak_id, 1)

                # 사용자가 틀렸을시 다시 OTP 추출하여 보내도록 하는 로직
                if not wrong_otp_state and is_state_check == -1:
                    print("사용자가 OTP번호를 틀려 다시 감지 합니다")
                    wrong_otp_state = True
                    already_send_otp = None    # OTP 재시도를 위해 초기화

                    # 60초가 경과하여 새롭게 갱신
                    if elapsed_time >= renew_duration:
                        start_time = current_time - renew_duration
                    else:
                        start_time = current_time

                # 60초가 경과하여 새롭게 OTP가 바뀐 경우
                if elapsed_time >= renew_duration and not renew_otp:
                    print(f"60초가 경과하여 OTP 갱신이 필요합니다. (경과 시간: {int(elapsed_time)}초)")
                    renew_otp = True
                    already_send_otp = None
                
                # 5초마다 사용자의 입력을 확인
                await asyncio.sleep(5)

            # 2분이 지나도 OTP가 통과되지 않은 경우
            if not otp_pass:
                print(f"OTP 인증 시간 초과 (총 경과 시간: {int(asyncio.get_event_loop().time() - start_time)}초)")
                raise OTPTimeoutError("OTP 인증 시간 초과")

            # 원격 나가기
            await self.remote.exit_remote()

            return otp_text

        except OTPTimeoutError as e:
            self.error_handler.handle_error(e, context="otp 인증 시간 초과", critical=True)
            raise
        except NoDetectionError as e:
            self.error_handler.handle_error(e, context="otp 감지 오류 발생", critical=True)
            raise
        except Exception as e:
            # 작업 상태 업데이트
            self.error_handler.handle_error(e, context="otp 체크 중 오류 발생", critical=True)
            raise

    async def execute_ten_min(self, ten_min_info:dict=None):
        """DO 실행 로직"""
        try:
            server_id = await self.state.unique_id().read_unique_id()
            worker_id = ten_min_info['worker_id']
            deanak_id = ten_min_info['deanak_id']

            # worker_id 검증 및 PC 번호 조회
            async with get_db_context() as db:
                pc_num = await self._validate_worker(db, server_id, worker_id)

            # 원격 연결 시작
            if not await self.remote.start_remote(worker_id=worker_id):
                return False

            # 10분 접속 프로그램 실행
            self.state.is_running = True  # Task 시작 전에 실행 상태 설정
            self.state.service_running_task = asyncio.create_task(self.auto_ten_min.ten_min_start(ten_min_info))
            
            # 태스크 완료 대기
            try:
                result = await self.state.service_running_task
                if not result:
                    print("10분 접속 작업 실패")
                    return False
            except Exception as e:
                print(f"10분 접속 작업 중 오류 발생: {e}")
                return False

            # 10분 접속 데이터 auto_ten_min테이블에 기입
            async with get_db_context() as db:
                print(f"10분 접속 프로그램 접속 완료 후 ten_min 데이터베이스 데이터 기입")
                await self.auto_ten_min_dao.insert_ten_min_start(db, deanak_id=deanak_id, server_id=server_id, pc_num=pc_num)

            # 10분 대기와 타이머 체크를 백그라운드에서 실행
            asyncio.create_task(self._wait_and_check_timer())

            return True

        except Exception as e:
            print(f"10분 접속 실행 중 오류 발생: {e}")
            return False

    async def _wait_and_check_timer(self):
        """10분 대기 후 타이머를 체크하는 백그라운드 태스크"""
        try:
            # 이전에 만약 겹쳤을시에 대기 중이었던 10분 접속 작업들을 처리
            await self.ten_min_timer_service.process_waiting_tasks()
            
            await asyncio.sleep(self.state.SERVICE_TIMER)  # 10분 대기
            
            print(f"타이머 완료")
            
            # 자신의 10분 접속을 처리하기 전에 만약 대기 중이었던 작업들이 있다면 차례대로 처리
            await self.ten_min_timer_service.process_waiting_tasks()

        except Exception as e:
            print(f"타이머 체크 중 오류 발생: {e}")

    async def stop_ten_min(self):
        """10분 접속 작업 중단"""
        self.state.is_running = False
        if self.state.service_running_task:
            await self.state.service_running_task
            self.state.service_running_task = None
