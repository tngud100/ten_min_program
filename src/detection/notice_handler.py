from src.utils.error_handler import NoDetectionError, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import time

class NoticeHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = MAX_DETECTION_ATTEMPTS
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_notice_screen(self, screen, loaded_templates, screen_state: ScreenState, deanak_id):
        """공지사항 화면을 처리합니다.
        
        Args:
            screen: 현재 화면 이미지
            loaded_templates: 로드된 템플릿 이미지들
            screen_state: 화면 상태 객체
            
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not screen_state.notice_passed and screen_state.password_passed:
                self.input_controller.press_key("esc")
                if screen_state.get_count("notice") > self.MAX_DETECTION_ATTEMPTS:
                    raise NoDetectionError(f"noticeScreen 화면이 {self.MAX_DETECTION_ATTEMPTS}회 이상 탐지되지 않았습니다.")
                
                if self.image_matcher.process_template(screen, 'team_select_screen', loaded_templates):
                    screen_state.notice_passed = True
                    print("공지사항 확인 완료")
                    time.sleep(1)
                    return True
            
            return False

        except NoDetectionError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.NO_DETECT_NOTICE_SCENE)
            raise e
