from enum import Enum

class ServiceState(Enum):
    """서비스 상태를 관리하는 Enum 클래스"""
    READY = "READY"        # 서비스 실행 준비 상태
    WAITING = "WAITING"    # 대기 상태
    WORKING = "WORKING"    # 작업 중 상태
    TERMINATED = "TERMINATED"  # 종료 상태
    TIMEOUT = "TIMEOUT"    # 시간 초과 상태
