
from PyQt5.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer
import sys
import logging
import asyncio
import queue

class LogWindow(QWidget):
    """GUI 로그 윈도우 클래스"""
    
    _instance = None
    _app = None
    _message_queue = queue.Queue()
    _is_shutting_down = False
    _on_close_callback = None

    def __init__(self):
        """LogWindow 초기화"""
        if LogWindow._instance is not None:
            raise Exception("This class is a singleton!")
            
        super().__init__()
        self._setup_ui()
        self._setup_logger()
        self._start_message_processor()
        LogWindow._instance = self

    def _setup_ui(self):
        """UI 컴포넌트 초기화"""
        self.setWindowTitle('Auto Deanak Log')
        self.setGeometry(100, 100, 600, 400)
        # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.log_display)
        self.setLayout(layout)

    def _setup_logger(self):
        """로거 설정"""
        class QTextEditHandler(logging.Handler):
            def emit(self, record):
                if not LogWindow._is_shutting_down:
                    msg = self.format(record)
                    LogWindow._message_queue.put(msg)

        self.logger = logging.getLogger('AutoDeanak')
        self.logger.setLevel(logging.INFO)

        handler = QTextEditHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def _start_message_processor(self):
        """메시지 처리 타이머 시작"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_messages)
        self.timer.start(100)

    def _process_messages(self):
        """큐에 있는 메시지 처리"""
        try:
            while not self._message_queue.empty() and not self._is_shutting_down:
                msg = self._message_queue.get_nowait()
                self.log_display.append(msg)
                self.log_display.verticalScrollBar().setValue(
                    self.log_display.verticalScrollBar().maximum()
                )
        except Exception as e:
            print(f"메시지 처리 중 오류 발생: {e}")

    def closeEvent(self, event):
        """윈도우 종료 이벤트 처리"""
        if self._on_close_callback and not self._is_shutting_down:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    event.ignore()
                    asyncio.create_task(self._on_close_callback())
                else:
                    event.accept()
            except Exception as e:
                print(f"종료 콜백 실행 중 오류 발생: {e}")
                event.accept()
        else:
            event.accept()

    def log(self, message):
        """동기적으로 로그 메시지 추가"""
        if not self._is_shutting_down:
            self._message_queue.put(message)

    async def async_log(self, message):
        """비동기적으로 로그 메시지 추가"""
        if not self._is_shutting_down:
            self._message_queue.put(message)

    @classmethod
    def initialize_app(cls):
        """QApplication 초기화"""
        if cls._app is None:
            if QApplication.instance() is None:
                try:
                    cls._app = QApplication(sys.argv)
                except Exception as e:
                    print(f"QApplication 초기화 오류: {e}")
                    return None
            else:
                cls._app = QApplication.instance()
        return cls._app

    @classmethod
    def get_instance(cls):
        """LogWindow 인스턴스 반환"""
        if cls._instance is None:
            if cls.initialize_app() is None:
                print("LogWindow를 초기화할 수 없습니다.")
                return None
            cls._instance = cls()
            cls._instance.show()
        return cls._instance

    @classmethod
    def set_close_callback(cls, callback):
        """종료 콜백 함수 설정"""
        cls._on_close_callback = callback
