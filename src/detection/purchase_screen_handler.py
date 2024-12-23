from src.utils.error_handler import SkipPurchaseException, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import time

class PurchaseScreenHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = 5
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_purchase_screen(self, screen, loaded_templates, screen_state: ScreenState):
        """구매 화면을 처리합니다.
        
        Args:
            screen: 현재 화면 이미지
            loaded_templates: 로드된 템플릿 이미지들
            screen_state: 화면 상태 객체
        
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not screen_state.purchase_screen_passed and screen_state.team_select_passed:
                if screen_state.get_count("purchase_before_main_screen") > self.MAX_DETECTION_ATTEMPTS:
                    raise SkipPurchaseException("메인 화면 전 구매 화면을 스킵합니다")
                
                top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates['purchase_before_main_screen'])
                print(f"구매 화면 존재 여부 확인 중...{screen_state.get_count("purchase_before_main_screen")}/{self.MAX_DETECTION_ATTEMPTS}")
                if top_left and bottom_right:
                    roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
                    if self.image_matcher.process_template(screen, 'purchase_cancel_btn', loaded_templates, click=True, roi=roi):
                        screen_state.purchase_screen_passed = True
                        print("구매 화면 처리 완료")
                        time.sleep(1)
                        return True
            
            return False

        except SkipPurchaseException as e:
            print(f"purchase_screen_handler: {e}")
            screen_state.purchase_screen_passed = True
            return True
