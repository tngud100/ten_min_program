import logging
import logging.handlers
import os
from datetime import datetime

def setup_logger():
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로거 생성
    logger = logging.getLogger('auto_daenak')
    logger.setLevel(logging.DEBUG)

    # 파일 핸들러 설정 (매일 자정에 로그 파일 변경)
    log_file = os.path.join(log_dir, f"auto_daenak_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 로거 인스턴스 생성
logger = setup_logger()
