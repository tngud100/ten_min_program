import os
import asyncio
from src.utils.image_matcher import ImageMatcher
from src.utils.capture import CaptureUtil
from src.utils.input_controller import InputController
from src.service.template_service import TemplateService

class OTPService:
    def __init__(self, image_matcher: ImageMatcher, capture: CaptureUtil, input: InputController, template_service: TemplateService):
        self.image_matcher = image_matcher
        self.capture = capture
        self.input = input
        self.template_service = template_service
    
    async def _extract_otp(self, screen, templates, max_attempts=5):
        """화면에서 OTP 추출"""
        attempt = 0
        while attempt < max_attempts:
            try:
                attempt += 1
                print(f"OTP 인식 시도 {attempt}/{max_attempts}...")
                
                top_left, bottom_right, _ = self.image_matcher.detect_template(screen, templates["otp_frame"])
                if not top_left or not bottom_right:
                    if attempt == max_attempts:
                        raise Exception("OTP 영역 찾기 실패")
                    print("OTP 영역 찾기 실패. 재시도 중...")
                    await asyncio.sleep(3)
                    continue
                
                # ROI 적용
                roi = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])

                # OTP 텍스트 추출
                otp_text = await self.image_matcher.extract_text(screen, templates["otp_number"], threshold=0.6, roi=roi)
                if not otp_text:
                    if attempt == max_attempts:
                        raise Exception("OTP 텍스트 추출 실패")
                    print("OTP 텍스트 추출 실패. 재시도 중...")
                    await asyncio.sleep(3)
                    continue
                
                print(f"인식된 OTP: {otp_text}")
                return otp_text
                
            except Exception as e:
                if attempt == max_attempts:
                    raise e
                print(f"오류 발생: {str(e)}. 재시도 중...")
                await asyncio.sleep(3)
                continue
        return None

    async def capture_and_extract_otp(self):
        """화면 캡처 후 OTP 추출"""
        await asyncio.sleep(1)  # UI가 완전히 로드될 때까지 대기
        screen = self.capture.screen_capture()
        if screen is None:
            raise Exception("화면 캡처 실패")

        templates = self.template_service.load_templates(["otp_frame", "otp_number"])
        return await self._extract_otp(screen, templates)