"""GUI 윈도우, 콘솔, 파일에 로그를 출력하는 모듈"""

import sys
import os
from datetime import datetime
from .log_window import LogWindow

class PrintLogger:
    """로그 출력 관리 (GUI 윈도우, 콘솔, 파일)"""
    
    _instance = None
    _initialized = False

    def __init__(self):
        if PrintLogger._instance is not None:
            raise Exception("이 클래스는 싱글톤입니다. initialize()를 사용하세요.")
        
        try:
            self.stdout = sys.stdout
        except:
            self.stdout = None
            
        self.log_window = None
        try:
            self.log_window = LogWindow.get_instance()
        except:
            pass
        
        self.log_dir = "logs/print"
        self.current_log_file = None
        os.makedirs(self.log_dir, exist_ok=True)
        self._create_new_log_file()
        
        PrintLogger._instance = self

    def _create_new_log_file(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_log_file = os.path.join(self.log_dir, f"log_{timestamp}.txt")

    @classmethod
    def initialize(cls):
        """PrintLogger 인스턴스 생성 또는 반환"""
        if not cls._initialized:
            try:
                instance = cls._instance or cls()
                sys.stdout = instance
                cls._initialized = True
                return instance
            except:
                return None
        return cls._instance

    def write(self, text):
        """로그 메시지 출력"""
        if not text or not text.strip():
            return
            
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            formatted_text = f"{timestamp} - {text.strip()}"

            # 파일에 로그 저장 (가장 중요)
            if self.current_log_file:
                try:
                    with open(self.current_log_file, 'a', encoding='utf-8') as f:
                        f.write(formatted_text + '\n')
                except:
                    pass

            # GUI 로그 윈도우 출력 (선택적)
            if self.log_window:
                try:
                    self.log_window.log(formatted_text)
                except:
                    pass

            # 콘솔 출력 (가능한 경우에만)
            if self.stdout:
                try:
                    self.stdout.write(formatted_text + '\n')
                    self.stdout.flush()
                except:
                    pass
                    
        except:
            pass  # 모든 로깅 실패 시 조용히 넘어감

    def flush(self):
        if self.stdout:
            try:
                self.stdout.flush()
            except:
                pass

    def __del__(self):
        if hasattr(self, 'stdout') and self.stdout:
            try:
                sys.stdout = self.stdout
            except:
                pass

    @classmethod
    def cleanup(cls):
        """리소스 정리"""
        if cls._instance:
            if hasattr(cls._instance, 'stdout') and cls._instance.stdout:
                try:
                    sys.stdout = cls._instance.stdout
                except:
                    pass
            cls._instance = None
            cls._initialized = False
