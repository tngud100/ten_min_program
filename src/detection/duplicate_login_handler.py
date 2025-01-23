from src.utils.error_handler import DuplicateLoginError, ErrorHandler
from src.utils.image_matcher import ImageMatcher
from src.utils.input_controller import InputController
from src.utils.capture import CaptureUtil

class DuplicateLoginHandler:
    def __init__(self, image_matcher: ImageMatcher, input_controller: InputController, capture: CaptureUtil):
        self.image_matcher = image_matcher
        self.input_controller = input_controller
        self.capture = capture
        self.error_handler = ErrorHandler()

    def check_duplicate_login(self, screen, loaded_templates, deanak_id):
        try:
            if self.image_matcher.process_template(screen, 'some_one_otp_pass_error', loaded_templates, threshold=0.8):
                raise DuplicateLoginError(self.error_handler.DUPLICATE_OTP_CHECK_ERROR)
            
            if self.image_matcher.process_template(screen, 'same_login_in_anykey_error', loaded_templates, threshold=0.8):
                raise DuplicateLoginError(self.error_handler.SAME_START_ERROR_BY_ANYKEY_SCENE)

            if self.image_matcher.process_template(screen, 'someone_already_login_error', loaded_templates, threshold=0.8):
                raise DuplicateLoginError(self.error_handler.DUPLICATE_CONNECTING_ERROR)

            if self.image_matcher.process_template(screen, 'some_one_connecting_try_error', loaded_templates, threshold=0.8):
                raise DuplicateLoginError(self.error_handler.SOMEONE_CONNECT_TRY_ERROR)

            if self.image_matcher.process_template(screen, 'same_login_in_password_error', loaded_templates, threshold=0.8):
                raise DuplicateLoginError(self.error_handler.SAME_START_ERROR_BY_PASSWORD_SCENE)
            
            return False
        except DuplicateLoginError as e:
            self.error_handler.handle_error(e, {"deanak_id" : deanak_id}, user_message=str(e))
            raise e