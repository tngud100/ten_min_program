import asyncio
from src.utils.error_handler import ErrorHandler, NoDetectionError
from src.models.screen_state import ScreenState
from src import state
import time

class ExitGameHandler:
    def __init__(self, image_matcher, capture, template_service, MAX_DETECTION_ATTEMPTS=5):
        self.image_matcher = image_matcher
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = MAX_DETECTION_ATTEMPTS
        self.state = state
        self.error_handler = ErrorHandler()
        self.screen_state = ScreenState()
        self.template_service = template_service
    
    async def _handle_screen_detection(self, screen_state, screen_type, loaded_templates, required_previous_state=None):
        if required_previous_state is not None and not required_previous_state:
            return False
            
        if getattr(screen_state, f"{screen_type}_screen_passed"):
            return True
        
        screen = self.capture.screen_capture()

        screen_state.increment_count(screen_type)
        if screen_state.get_count(screen_type) > self.MAX_DETECTION_ATTEMPTS:
            raise NoDetectionError(f"{screen_type} 화면이 {self.MAX_DETECTION_ATTEMPTS}회 이상 탐지되지 않았습니다.")
        
        top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates[screen_type])
        if top_left and bottom_right:
            roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
            if self.image_matcher.process_template(screen, f"{screen_type}_btn", loaded_templates, click=True, roi=roi):
                setattr(screen_state, f"{screen_type}_screen_passed", True)
                time.sleep(1)
                return True

        return False

    async def handle_exit_game_screen(self, deanak_id):
        try:
            # self.loaded_templates, self.state.screen_state,
            loaded_templates = self.template_service.get_templates()
            
            self.screen_state.reset_all()  # 상태 초기화

            while not self.screen_state.exit_modal_screen_passed:
                await self._handle_screen_detection(
                    self.screen_state, "exit_team",
                    loaded_templates=loaded_templates
                )
                await asyncio.sleep(1)

                await self._handle_screen_detection(
                    self.screen_state, "exit_modal",
                    required_previous_state=self.screen_state.exit_team_screen_passed,
                    loaded_templates=loaded_templates
                )
                await asyncio.sleep(2)

        except NoDetectionError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.NO_DETECT_EXIT_GAME_SCREEN_SCENE)
            raise e