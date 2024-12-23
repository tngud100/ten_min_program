from src.utils.error_handler import NoDetectionError, WrongPasswordError, TemplateEmptyError
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

from src.detection.password_handler import PasswordHandler
from src.detection.notice_handler import NoticeHandler
from src.detection.ten_min_handler import TenMinScreenHandler
import asyncio

class AutoTenMin:
    def __init__(self, image_matcher: ImageMatcher, input_controller: InputController, template_service: TemplateService, capture: CaptureUtil, state: state, remote_pcs_dao: RemoteDao, remote: RemoteController, auto_ten_min_dao: AutoTenMinDao):
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
        # 핸들러 초기화
        self.password_handler = PasswordHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)
        self.notice_handler = NoticeHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)
        self.ten_min_screen_handler = TenMinScreenHandler(self.image_matcher, self.input_controller, self.capture, self.MAX_DETECTION_ATTEMPTS)

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
                    
                    if not self.screen_state.password_passed:
                        self.screen_state.increment_count("password")
                    if not self.screen_state.notice_passed and self.screen_state.password_passed:
                        self.screen_state.increment_count("notice")
                    if not self.screen_state.team_select_passed and self.screen_state.notice_passed:
                        self.screen_state.increment_count("team_select")
                        
                    if self.password_handler.handle_password_screen(screen, loaded_templates, password_list, self.screen_state):
                        continue

                    if self.notice_handler.handle_notice_screen(screen, loaded_templates, self.screen_state):
                        continue

                    if self.ten_min_screen_handler.handle_ten_min_screen(screen, loaded_templates, self.screen_state):
                        continue
                        
                    if self.screen_state.team_select_passed:
                        print("10분접속 시작")
                        self.state.is_running = False
                        await self.remote.exit_remote()

                        # 작업 상태 업데이트
                        async with get_db_context() as db:
                            await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'waiting')
                            await self.auto_ten_min_dao.update_ten_min_state(db, deanak_id=deanak_id, server_id=server_id, state=ServiceState.WAITING)
                        return True

                    await asyncio.sleep(2)

                except (NoDetectionError, WrongPasswordError, TemplateEmptyError) as e:
                    async with get_db_context() as db:
                        await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'stopped')
                    self.error_handler.handle_error(e, "10분 접속 처리 중 오류 발생")
                    self.state.is_running = False

                except Exception as screen_error:
                    async with get_db_context() as db:
                        await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, 'stopped')
                    self.error_handler.handle_error(screen_error, "10분 접속 처리 중 알 수 없는 오류 발생")
                    self.state.is_running = False

        except ValueError as ve:
            self.error_handler.handle_error(ve, "유효성 검사 실패")
            self.state.is_running = False
            
        except Exception as e:
            self.error_handler.handle_error(e, "작업 실패")
            self.state.is_running = False
            print("작업실패")