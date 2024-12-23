from src.utils.error_handler import SkipTopClassException, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import time

class TopClassScreenHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = 3
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_top_class_screen(self, screen, loaded_templates, screen_state: ScreenState):
        """구매 화면을 처리합니다.
        
        Args:
            screen: 현재 화면 이미지
            loaded_templates: 로드된 템플릿 이미지들
            screen_state: 화면 상태 객체
        
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not screen_state.top_class_screen_passed and screen_state.get_all_btn_screen_passed:
                if screen_state.get_count("top_class_screen") > self.MAX_DETECTION_ATTEMPTS:
                    raise SkipTopClassException("탑클래스 없음")
                
                top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates['top_class_screen'])
                print(f"탑클래스 화면 존재 여부 확인 중...{screen_state.get_count("top_class_screen")}/{self.MAX_DETECTION_ATTEMPTS}")
                if top_left and bottom_right:
                    roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
                    if self.image_matcher.process_template(screen, 'top_class_cancel_btn', loaded_templates, click=True, roi=roi):
                        screen_state.top_class_screen_passed = True
                        print("탑클래스 화면 처리 완료")
                        time.sleep(1)
                        return True
            
            return False

        except SkipTopClassException as e:
            print(f"{e}")
            screen_state.top_class_screen_passed = True
            return True
