from src.utils.error_handler import NoDetectionError, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import random
import time

class TeamSelectHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = MAX_DETECTION_ATTEMPTS
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_team_select_screen(self, screen, loaded_templates, screen_state: ScreenState):
        """팀 선택 화면을 처리합니다.
        
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
                    # 팀 선택 텍스트 탐지
                    top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates['team_select_text'], threshold=0.8)
                    
                    if top_left and bottom_right:
                        box_height = bottom_right[1] - top_left[1]
                        offset_y = top_left[1] + box_height * 5
                        
                        self.input_controller.click(random.randint(top_left[0], bottom_right[0]), offset_y)
                        screen_state.team_select_passed = True
                        print("팀 선택 완료")
                        time.sleep(5)
                        return True
            
            return False

        except NoDetectionError as e:
            raise e