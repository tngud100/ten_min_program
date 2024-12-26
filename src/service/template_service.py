import os
import cv2
from src.utils.image_matcher import ImageMatcher

class TemplateEmptyError(Exception):
    pass

class TemplateService:
    def __init__(self, image_matcher: ImageMatcher):
        self.image_matcher = image_matcher
        self.TEMPLATES = {
            # OTP 관련 템플릿
            "otp_frame": 'static/image/otpFrame.PNG',
            "otp_number": 'static/image/otpNumber.PNG',
            "otp_wrong": 'static/image/otpWrong.PNG',
            # 대낙 관련 템플릿
            "password_screen": 'static/image/passwordScreen.PNG',
            "password_confirm": 'static/image/loginConfirm.PNG',
            "wrong_password": 'static/image/wrongPassword.PNG',
            "notice_screen": 'static/image/notice.PNG',
            "team_select_screen": 'static/image/selectTeam.PNG',
            "team_select_text": 'static/image/selectTeamText.PNG',
            "purchase_before_main_screen": 'static/image/beforeMainPurchases.PNG',
            "purchase_cancel_btn": 'static/image/purchaseCloseBtn.PNG',
            "main_screen": 'static/image/mainScreen.PNG',
            "market_screen": 'static/image/marketScreen.PNG',
            "get_item_screen": 'static/image/getItemScreen.PNG',
            "get_all_screen": 'static/image/getAllScreen.PNG',
            "top_class": 'static/image/topClass.PNG',
            "no_top_class": 'static/image/noTopClass.PNG',
            "market_btn": 'static/image/market.PNG',
            "list_btn": 'static/image/sellList.PNG',
            "get_item_btn": 'static/image/getItemConfirm.PNG',
            "arrange_btn_screen": 'static/image/PriceArrangeScreen.PNG',
            "arrange_btn": 'static/image/priceArrangeBtn.PNG',
            "price_desc": 'static/image/priceDesc.PNG',
            "get_all_btn_screen": 'static/image/getAllScreen.PNG',
            "get_all_btn": 'static/image/getAll.PNG',
            "top_class_screen": 'static/image/noUseTopclassGetModal.PNG',
            "top_class_cancel_btn": 'static/image/noUseTopclassGetConfirm.PNG',
        }
        self._template_cache = {}

    def _load_template(self, template_path: str):
        """단일 템플릿 이미지를 로드하고 캐싱"""
        try:
            # 캐시 확인
            if template_path in self._template_cache:
                return self._template_cache[template_path]

            # 파일 존재 확인
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"템플릿 파일이 존재하지 않습니다: {template_path}")

            # 템플릿 로드
            template = cv2.imread(template_path)
            if template is None:
                raise Exception(f"템플릿 로드 실패: {template_path}")

            # 흑백 변환
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # 캐시에 저장
            self._template_cache[template_path] = template
            
            return template

        except Exception as e:
            print(f"템플릿 로드 중 오류 발생: {e}")
            return None

    def load_templates(self, template_keys: list):
        """지정된 키에 해당하는 템플릿 이미지들을 로드
        
        Args:
            template_keys (list): 로드할 템플릿 키 목록 (예: ["otp_frame", "otp_number"])
            
        Returns:
            dict: 템플릿 키와 로드된 이미지의 딕셔너리
            
        Raises:
            Exception: 템플릿 파일이 없거나 로드 실패시
        """
        templates = {}
        for key in template_keys:
            if key not in self.TEMPLATES:
                raise Exception(f"존재하지 않는 템플릿 키: {key}")
                
            path = self.TEMPLATES[key]
            template = self._load_template(path)
            if template is None:
                raise Exception(f"템플릿 로드 실패: {path}")
                
            templates[key] = template
            
        return templates

    def load_password_templates(self, password_list: list):
        """비밀번호 템플릿 로드"""
        templates = {}
        for password in password_list:
            path = f'static/image/{password}.PNG'
            template = self._load_template(path)
            if template is None:
                raise Exception(f"비밀번호 템플릿 로드 실패: {path}")
            templates[password] = template
        return templates

    def get_templates(self, password_list: list = None):
        """모든 템플릿 이미지를 로드하고 반환합니다.

        Args:
            password_list (list, optional): 비밀번호 템플릿을 로드할 비밀번호 목록. Defaults to None.

        Returns:
            dict: 모든 템플릿 키와 로드된 이미지의 딕셔너리

        Raises:
            TemplateEmptyError: 템플릿 파일이 없거나 로드 실패시
        """
        try:
            templates = {}
            
            # 기본 템플릿 로드
            for key in self.TEMPLATES.keys():
                path = self.TEMPLATES[key]
                
                # 캐시된 템플릿이 있으면 사용
                if key in self._template_cache:
                    templates[key] = self._template_cache[key]
                    continue
                
                
                # 템플릿 파일 존재 확인
                if not os.path.exists(path):
                    raise TemplateEmptyError(f"템플릿 파일이 존재하지 않습니다: {path}")
                
                # 템플릿 로드
                template = self._load_template(path)
                if template is None:
                    raise TemplateEmptyError(f"템플릿 로드에 실패했습니다: {path}")
                
                templates[key] = template
                self._template_cache[key] = template  # 캐시에 저장
            
            # 비밀번호 템플릿 로드
            if password_list:
                password_templates = self.load_password_templates(password_list)
                templates["password_templates"] = password_templates
                
            if not templates:
                raise TemplateEmptyError("로드된 템플릿이 없습니다.")
                
            return templates
            
        except Exception as e:
            if isinstance(e, TemplateEmptyError):
                raise
            raise TemplateEmptyError(f"템플릿 로드 중 오류 발생: {str(e)}")

    def clear_cache(self):
        """템플릿 캐시 초기화"""
        self._template_cache.clear()
