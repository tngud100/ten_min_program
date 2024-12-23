import os
from dotenv import load_dotenv
from pathlib import Path

# 기본 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# 환경 설정
ENV = os.getenv('ENV', 'development')  # 기본값은 development

# .env 파일 로드
env_file = BASE_DIR / '.env'
if env_file.exists():
    load_dotenv(env_file)

# 데이터베이스 설정
DB_CONFIG = {
    'development': {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "passwd": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "auto_daenak_dev")
    },
    'production': {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "passwd": os.getenv("DB_PASSWORD"),
        "db": os.getenv("DB_NAME")
    }
}[ENV]

# MySQL Binlog 설정
BINLOG_CONFIG = {
    "tables": ["remote_pcs", "deanak"],
    "schema": os.getenv("DB_NAME"),
}

# 재시도 설정
RETRY_CONFIG = {
    "max_retries": int(os.getenv("MAX_RETRIES", "5")),
    "retry_delay": int(os.getenv("RETRY_DELAY", "5"))
}

# 애플리케이션 설정
APP_CONFIG = {
    "service_name": "ten_min",
    "log_dir": BASE_DIR / "logs",
    "unique_id_file": BASE_DIR / "unique_id.txt"
}
