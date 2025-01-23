from src.utils.error_handler import NoDetectionError, WrongPasswordError, TemplateEmptyError, ErrorHandler
from src.models.screen_state import ScreenState
from src import state
import time

class PasswordHandler:
    def __init__(self, image_matcher, input_controller, capture, MAX_DETECTION_ATTEMPTS=3):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.MAX_DETECTION_ATTEMPTS = MAX_DETECTION_ATTEMPTS
        self.state = state
        self.error_handler = ErrorHandler()

    def handle_password_screen(self, screen, loaded_templates, password_list, screen_state: ScreenState, deanak_id):
        """비밀번호 화면을 처리합니다.
        Args:
            screen: 현재 화면 이미지
            loaded_templates: 로드된 템플릿 이미지들
            password_list: 입력할 비밀번호 리스트
            screen_state: 화면 상태 객체
            
        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not screen_state.password_passed:
                self.input_controller.press_key("esc")
                
                if screen_state.get_count("password") > self.MAX_DETECTION_ATTEMPTS:
                    raise NoDetectionError(f"passwordScreen 화면이 {self.MAX_DETECTION_ATTEMPTS}회 이상 탐지되지 않았습니다.")
                
                top_left, bottom_right, _ = self.image_matcher.detect_template(screen, loaded_templates['password_screen'])
                if top_left and bottom_right:
                    roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

                    for template_key in password_list:
                        if template_key not in loaded_templates['password_templates']:
                            raise TemplateEmptyError(f"비밀번호 템플릿이 없습니다: {template_key}")
                        
                        # 비밀번호 입력스크린 감지
                        self.image_matcher.process_template(screen, template_key, loaded_templates['password_templates'], click=True, roi=roi)
                        time.sleep(0.5)

                    # 비밀번호 확인 클릭
                    if self.image_matcher.process_template(screen, 'password_confirm', loaded_templates, click=True, roi=roi):
                        time.sleep(3)
                        for i in range(3):
                            screen = self.capture.screen_capture()
                            time.sleep(1)
                            if self.image_matcher.process_template(screen, 'wrong_password', loaded_templates, threshold=0.8, roi=roi):
                                raise WrongPasswordError("비밀번호 오류")
                        
                        screen_state.password_passed = True
                        print("비밀번호 입력 완료")
                        return True
            
            return False

        except NoDetectionError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.NO_DETECT_PASSWORD_SCENE)
            raise e

        except WrongPasswordError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.WRONG_PASSWORD_ERROR)
            raise e

        except TemplateEmptyError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=self.error_handler.EMPTY_PASSWORD_TEMPLATE)
            raise e
