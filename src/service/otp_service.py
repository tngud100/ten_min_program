import os
import asyncio
from src.utils.image_matcher import ImageMatcher
from src.utils.capture import CaptureUtil
from src.utils.input_controller import InputController
from src.service.template_service import TemplateService
from src.utils.error_handler import OTPOverTimeDetectError, NoDetectionError, TemplateEmptyError

class OTPService:
    def __init__(self, image_matcher: ImageMatcher, capture: CaptureUtil, input: InputController, template_service: TemplateService):
        self.image_matcher = image_matcher
        self.capture = capture
        self.input = input
        self.template_service = template_service
    
    async def _extract_otp(self, templates, max_attempts=10):
        """화면에서 OTP 추출"""
        attempt = 0
        while attempt < max_attempts:
            screen = self.capture.screen_capture()
            if screen is None:
                raise NoDetectionError("otp 화면 캡처 중 화면 캡처 실패")
            
            attempt += 1
            print(f"OTP 인식 시도 {attempt}/{max_attempts}...")
            
            top_left, bottom_right, _ = self.image_matcher.detect_template(screen, templates["otp_frame"], threshold=0.6)
            if not top_left or not bottom_right:
                if attempt == max_attempts:
                    raise OTPOverTimeDetectError("OTP 감지 횟수 초과 - OTP FRAME")
                print("OTP 영역 찾기 실패. 재시도 중...")
                await asyncio.sleep(3)
                continue
            
            # ROI 적용
            roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

            # OTP 텍스트 추출
            otp_text = await self.image_matcher.extract_text(screen, templates["otp_number"], threshold=0.6, roi=roi)
            if not otp_text:
                if attempt == max_attempts:
                    raise OTPOverTimeDetectError("OTP 감지 횟수 초과 - OTP TEXT")
                print("OTP 텍스트 추출 실패. 재시도 중...")
                await asyncio.sleep(3)
                continue
            
            print(f"인식된 OTP: {otp_text}")
            return otp_text

        return False

    async def _wrong_otp_detect(self, templates):
        """틀린 OTP 감지"""
        try:
            screen = self.capture.screen_capture()
            if screen is None:
                raise NoDetectionError("실패 otp 화면 캡처 중 캡처 실패")

            top_left, bottom_right, _ = self.image_matcher.detect_template(screen, templates["otp_frame"], threshold=0.6)

            if not top_left or not bottom_right:
                print("OTP 영역 사라짐")
                return 1
            
            # ROI 적용
            roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

            # OTP 텍스트 추출
            otp_wrong = await self.image_matcher.extract_text(screen, templates["otp_wrong"], threshold=0.6, roi=roi)
            if not otp_wrong:
                # print("사용자 입력을 기다리고 있습니다.")
                return 0

            # print(f"추출한 텍스트: {otp_wrong}")
            # print("사용자가 비밀번호를 틀렸습니다.")
            
            return -1
    
        except NoDetectionError as e:
            raise NoDetectionError(str(e));

    async def pass_or_wrong_otp_detect(self):
        """화면 캡처 후 틀린 OTP 입력 감지"""
        try:
            await asyncio.sleep(1)  # UI가 완전히 로드될 때까지 대기

            templates = self.template_service.load_templates(["otp_frame", "otp_wrong"])
            return await self._wrong_otp_detect(templates)

        except (TemplateEmptyError, NoDetectionError):
            raise


    async def capture_and_extract_otp(self):
        """화면 캡처 후 OTP 추출"""
        try:
            await asyncio.sleep(1)  # UI가 완전히 로드될 때까지 대기

            templates = self.template_service.load_templates(["otp_frame", "otp_number"])
            return await self._extract_otp(templates)
        except (TemplateEmptyError, NoDetectionError, OTPOverTimeDetectError):
            raise