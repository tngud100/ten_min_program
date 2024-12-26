import logging
import traceback
from datetime import datetime
import os
from database import get_db_context
from src.dao.remote_pcs_dao import RemoteDao
from src import state

class NoDetectionError(Exception):
    pass
class WrongPasswordError(Exception):
    pass
class TemplateEmptyError(Exception):
    pass
class SkipPurchaseException(Exception):
    pass
class SkipTopClassException(Exception):
    pass
class NoWorkerError(Exception):
    pass
class CantFindPcNumError(Exception):
    pass
class OTPTimeoutError(Exception):
    pass
class CantFindTenMinDataError(Exception):
    pass
class NotChangedPCStateError(Exception):
    pass

class ErrorHandler:
    def __init__(self):
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.setup_logger()
        self.remote_pcs_dao = RemoteDao()
        self.unique_id = state.unique_id()

    def setup_logger(self):
        """로거 설정"""
        log_file = os.path.join(self.log_dir, f"error_{datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            encoding='utf-8'  # UTF-8 인코딩 설정
        )

    def handle_error(self, error, context=None, critical=False, user_message=None):
        """에러 처리"""
        try:
            # 오류 메시지 포맷 설정
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            exception_type = type(error).__name__
            tb = traceback.format_exc()  # 전체 스택 트레이스를 문자열로 변환
            context_str = context if context else ""
            full_message = (
                f"Timestamp: {timestamp}\n"
                f"Exception Type: {exception_type}\n"
                f"Context: {context_str}\n"
                f"Error Details: {error}\n"
                f"Traceback:\n{tb}\n"
                + "-"*80 + "\n"
            )
            # print(f"full_message: {full_message}")
            # 로그 기록
            logging.error(full_message)
            
            # 심각한 에러 처리
            if critical:
                print("Critical error occurred.")
                # 추가적인 알림이나 조치를 여기에 추가
            
            # 사용자에게 알림 (옵션)
            if user_message:
                print(user_message)

            return {
                'error': str(error),
                'context': context,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"ErrorHandler에서 오류 발생: {e}")
            return None

    def get_error_logs(self, date=None):
        """에러 로그 조회"""
        try:
            if date:
                log_file = os.path.join(self.log_dir, f"error_{date}.log")
            else:
                log_file = os.path.join(self.log_dir, f"error_{datetime.now().strftime('%Y%m%d')}.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.readlines()
            return []
        except Exception as e:
            print(f"로그 조회 중 오류 발생: {e}")
            return []
