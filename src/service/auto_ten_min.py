import datetime as dt
from src.utils.error_handler import DuplicateLoginError, TenMinError, APICallError, NoDetectionError, WrongPasswordError, TemplateEmptyError
from src.utils.image_matcher import ImageMatcher
from src.utils.input_controller import InputController
from src.utils.remote_controller import RemoteController
from src.service.template_service import TemplateService
from src.utils.capture import CaptureUtil
from src.utils.error_handler import ErrorHandler
from src.models.screen_state import ScreenState
from src import state
from database import get_db_context
from src.dao.remote_pcs_dao import RemoteDao
from src.dao.auto_ten_min_dao import AutoTenMinDao
from src.models.service_state import ServiceState
from src.utils.api import Api

from src.detection.password_handler import PasswordHandler
from src.detection.notice_handler import NoticeHandler
from src.detection.ten_min_handler import TenMinScreenHandler
from src.detection.duplicate_login_handler import DuplicateLoginHandler
import asyncio

class AutoTenMin:
    def __init__(self, image_matcher: ImageMatcher, input_controller: InputController, template_service: TemplateService, capture: CaptureUtil, state: state, remote_pcs_dao: RemoteDao, remote: RemoteController, auto_ten_min_dao: AutoTenMinDao, api: Api):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.template_service = template_service
        self.capture = capture
        self.error_handler = ErrorHandler()
        self.state = state
        self.MAX_DETECTION_ATTEMPTS = 20
        self.screen_state = ScreenState()
        self.remote_pcs_dao = remote_pcs_dao
        self.remote = remote
        self.auto_ten_min_dao = auto_ten_min_dao
        self.api = api
        # 핸들러 초기화
        self.password_handler = PasswordHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)
        self.notice_handler = NoticeHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)
        self.ten_min_screen_handler = TenMinScreenHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)
        self.duplicate_login_handler = DuplicateLoginHandler(self.image_matcher, self.input_controller, self.capture)

    async def _getter_info(self, deanak_info):
        worker_id = deanak_info['worker_id']
        password_list = list(str(deanak_info['pw2']))
        server_id = await self.state.unique_id().read_unique_id()
        deanak_id = deanak_info['deanak_id']
        return worker_id, password_list, server_id, deanak_id

    async def ten_min_start(self, deanak_info:dict=None):
        """대낙 프로세스 시작"""
        try:
            if not deanak_info:
                raise ValueError("대낙 정보가 없습니다.")
            
            worker_id, password_list, server_id, deanak_id = await self._getter_info(deanak_info)
            print(worker_id, password_list)
            
            try:
                loaded_templates = self.template_service.get_templates(password_list)
            except TemplateEmptyError as e:
                self.error_handler.handle_error(e, "템플릿 로드 실패")
                return False
            
            self.screen_state.reset_all()  # 상태 초기화
            
            self.state.is_running = True
            while self.state.is_running:
                try:
                    screen = self.capture.screen_capture()
                    print("capturing...")

                    self.duplicate_login_handler.check_duplicate_login(screen, loaded_templates, deanak_id)

                    if not self.screen_state.password_passed:
                        self.screen_state.increment_count("password")
                    if not self.screen_state.notice_passed and self.screen_state.password_passed:
                        self.screen_state.increment_count("notice")
                    if not self.screen_state.team_select_passed and self.screen_state.notice_passed:
                        self.screen_state.increment_count("team_select")
                        
                    if self.password_handler.handle_password_screen(screen, loaded_templates, password_list, self.screen_state, deanak_id):
                        continue

                    if self.notice_handler.handle_notice_screen(screen, loaded_templates, self.screen_state, deanak_id):
                        continue

                    if self.ten_min_screen_handler.handle_ten_min_screen(screen, loaded_templates, self.screen_state, deanak_id):
                        continue
                        
                    if self.screen_state.team_select_passed:
                        print("10분접속 시작")
                        self.state.is_running = False
                        # await self.remote.exit_remote()

                        # 작업 상태 업데이트
                        async with get_db_context() as db:
                            await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'waiting')
                            await self.auto_ten_min_dao.update_ten_min_state(db, deanak_id=deanak_id, server_id=server_id, state=ServiceState.WAITING)
                            # await self.api.send_waiting(deanak_id)
                        return True

                    await asyncio.sleep(2)

                except (NoDetectionError, WrongPasswordError, TemplateEmptyError, APICallError, DuplicateLoginError) as e:
                    async with get_db_context() as db:
                        await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'stopped')
                    self.state.is_running = False
                    return False
                    
                except Exception as screen_error:
                    async with get_db_context() as db:
                        await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'stopped')
                    self.error_handler.handle_error(screen_error, {"deanak_id": deanak_id}, user_message=self.error_handler.TEN_MIN_ERROR)
                    self.state.is_running = False
                    return False

        except (Exception, ValueError) as e:
            self.state.is_running = False
            raise TenMinError("10분 작업 중 오류 - ten_min_start함수 내")


    async def check_duplicate_login(self, deanak_id):
        try:
            loaded_templates = self.template_service.get_templates()
            current_time = dt.datetime.now()
            timer_delta = dt.timedelta(seconds=self.state.SERVICE_TIMER)
            end_time = current_time + timer_delta
            while (end_time - dt.datetime.now()).total_seconds() > 0:
                screen = self.capture.screen_capture()
                await asyncio.sleep(30)
                print("중복 접속 체크")
                self.duplicate_login_handler.check_duplicate_login(screen, loaded_templates, deanak_id)

            return True

        except DuplicateLoginError as e:
            return False