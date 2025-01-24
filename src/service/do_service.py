import asyncio
from src.models import deanak
from src.utils.remote_controller import RemoteController
from src.utils.error_handler import CantFindRemoteProgram, DuplicateLoginError, TenMinError, ErrorHandler, CheckTimerError, CantFindTenMinDataError, OTPError, NoWorkerError, CantFindPcNumError, OTPTimeoutError, NoDetectionError, OTPOverTimeDetectError, TemplateEmptyError
from src.dao.remote_pcs_dao import RemoteDao
from src.service.auto_ten_min import AutoTenMin
from src.dao.auto_ten_min_dao import AutoTenMinDao
from database import get_db_context
from src.service.otp_service import OTPService
from src.service.ten_min_timer_service import TenMinTimerService
from src import state
from src.models.service_state import ServiceState
from src.dao.deanak_dao import DeanakDao
from src.utils.api import Api

class DoService:
    def __init__(self, remote: RemoteController, error_handler: ErrorHandler, state: state, deanak_dao: DeanakDao,
                 remote_pcs_dao: RemoteDao, otp_service: OTPService, auto_ten_min: AutoTenMin, ten_min_timer_service: TenMinTimerService, auto_ten_min_dao: AutoTenMinDao, api: Api):
        self.remote = remote
        self.error_handler = error_handler
        self.remote_pcs_dao = remote_pcs_dao
        self.otp_service = otp_service
        self.auto_ten_min = auto_ten_min
        self.ten_min_timer_service = ten_min_timer_service
        self.auto_ten_min_dao = auto_ten_min_dao    
        self.state = state
        self.deanak_dao = deanak_dao
        self.api = api

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
            timeout_duration = 135  # 2분
            renew_duration = 65

            async with get_db_context() as db:
                pc_num = await self._validate_worker(db, server_id, worker_id)

            # 원격 연결 시작
            # if not await self.remote.start_remote(pc_num):
            #     return False

            # 2분 동안만 실행
            while (asyncio.get_event_loop().time() - start_time) < timeout_duration:
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
                    if not otp_text:
                        print("OTP 추출 실패")
                        print("다시 인식을 시작합니다")
                    else:
                        # OTP 보내기
                        if await self.api.send_otp(deanak_id, otp_text):
                            already_send_otp = otp_text

                if already_send_otp is not None:
                    is_state_check = await self.otp_service.pass_or_wrong_otp_detect() # 0이면 이상 없음, 1이면 통과, -1이면 틀림

                # 통과로 state업데이트
                if is_state_check == 1:
                    print("OTP 통과, 게임 실행")
                    async with get_db_context() as db:
                        await self.deanak_dao.update_otp_pass(db, deanak_id, 1)

                if is_state_check == 0:
                    print("사용자의 입력이 {}/{}번 틀렸습니다.".format(0, 1))
                    print("사용자의 입력을 기다리고 있습니다.")

                if is_state_check == -1 and wrong_otp_state:
                    print("사용자의 입력이 {}/{}번 틀렸습니다.".format(1, 1))
                    print("사용자의 입력을 기다리고 있습니다.")

                # 사용자가 틀렸을시 다시 OTP 추출하여 보내도록 하는 로직
                if not wrong_otp_state and is_state_check == -1:
                    print("다시 감지를 시작합니다")
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
                
                # 3초마다 사용자의 입력을 확인
                await asyncio.sleep(3)

            # 2분이 지나도 OTP가 통과되지 않은 경우
            if not otp_pass:
                print(f"OTP 인증 시간 초과 (총 경과 시간: {int(asyncio.get_event_loop().time() - start_time)}초)")
                raise OTPTimeoutError("OTP 인증 시간 초과")

            # # 원격 나가기
            # await self.remote.exit_remote()

            return otp_text

        except (OTPTimeoutError, NoDetectionError, OTPOverTimeDetectError,
                NoDetectionError, TemplateEmptyError, NoWorkerError, CantFindPcNumError,
                CantFindRemoteProgram) as e:
            raise
        except Exception as e:
            # 알 수 없는 예외만 OTPError로 감싸기
            raise OTPError(f"OTP 감지 중 알 수 없는 오류 발생: {str(e)}")

    async def execute_ten_min(self, ten_min_info:dict=None):
        """DO 실행 로직"""
        try:
            server_id = await self.state.unique_id().read_unique_id()
            worker_id = ten_min_info['worker_id']
            deanak_id = ten_min_info['deanak_id']

            # worker_id 검증 및 PC 번호 조회
            async with get_db_context() as db:
                pc_num = await self._validate_worker(db, server_id, worker_id)

            # # 원격 연결 시작
            # if not await self.remote.start_remote(pc_num):
            #     return False

            # 10분 접속 프로그램 실행
            self.state.is_running = True  # Task 시작 전에 실행 상태 설정
            self.state.service_running_task = asyncio.create_task(self.auto_ten_min.ten_min_start(ten_min_info))
            
            # 태스크 완료 대기
            success = await self.state.service_running_task
            
            # 성공적으로 완료된 경우에만 데이터베이스에 기입
            if not success:
                return False

            async with get_db_context() as db:
                print(f"10분 접속 프로그램 접속 완료 후 ten_min 데이터베이스 데이터 기입")
                await self.auto_ten_min_dao.insert_ten_min_start(db, deanak_id=deanak_id, server_id=server_id, pc_num=pc_num)
            
            # 10분 대기와 타이머 체크를 백그라운드에서 실행
            waiting = asyncio.create_task(self._wait_and_check_timer(deanak_id))
            ten_min = await waiting
            if not ten_min:
                return False

            return True
                

        
        except (TenMinError, ValueError, TemplateEmptyError, NoWorkerError,
                CantFindPcNumError, CantFindRemoteProgram, CantFindTenMinDataError,
                CheckTimerError) as e:
            raise
        except Exception as e:
            print(f"10분 접속 실행 중 오류 발생: {e}")
            return False

    async def _wait_and_check_timer(self, deanak_id):
        """10분 대기 후 타이머를 체크하는 백그라운드 태스크"""
        try:
            # 이전에 만약 겹쳤을시에 대기 중이었던 10분 접속 작업들을 처리
            # await self.ten_min_timer_service.process_waiting_tasks()
            
            try:
                if await self.auto_ten_min.check_duplicate_login(deanak_id):
                    return False
            except DuplicateLoginError:
                return False
            
            print(f"타이머 완료")
            await asyncio.sleep(2)
            # 현재 서버의 state가 working인 인스턴스가 있으면 패스

            
            # 자신의 10분 접속을 처리하기 전에 만약 대기 중이었던 작업들이 있다면 차례대로 처리
            await self.ten_min_timer_service.process_waiting_tasks()
            return True


        except CantFindTenMinDataError as e:
            raise
        except (Exception, CheckTimerError) as e:
            raise CheckTimerError
        
    async def stop_ten_min(self):
        """10분 접속 작업 중단"""
        self.state.is_running = False
        if self.state.service_running_task:
            try:
                await self.state.service_running_task
            except asyncio.CancelledError:
                pass  # 태스크가 취소되어도 정상적으로 처리
            finally:
                self.state.service_running_task = None
