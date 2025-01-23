from src.utils.error_handler import NoDetectionError, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import random
import time

class TenMinScreenHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = MAX_DETECTION_ATTEMPTS
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_ten_min_screen(self, screen, loaded_templates, screen_state: ScreenState, deanak_id):
        """10분 모드을 처리합니다.
        
        Args:
            screen: 현재 화면 이미지
            loaded_templates: 로드된 템플릿 이미지들
            screen_state: 화면 상태 객체
            
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not screen_state.team_select_passed and screen_state.notice_passed:
                if screen_state.get_count("team_select") > self.MAX_DETECTION_ATTEMPTS:
                    raise NoDetectionError(f"team_select_screen 화면이 {self.MAX_DETECTION_ATTEMPTS}회 이상 탐지되지 않았습니다.")
                
                # 팀 선택 화면 탐지
                top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates['team_select_screen'], threshold=0.8)
                if top_left and bottom_right:
                    screen_state.team_select_passed = True

                    return True
                    
            return False

        except NoDetectionError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.NO_DETECT_TEAM_SELECT_SCENE)
            raise e