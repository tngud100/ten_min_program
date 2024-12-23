from dataclasses import dataclass
from typing import Dict

@dataclass
class ScreenState:
    """화면 상태를 관리하는 클래스"""
    # 화면 통과 상태
    password_passed: bool = False
    notice_passed: bool = False
    team_select_passed: bool = False
    # 화면 감지 시도 횟수
    detection_counts: Dict[str, int] = None

    def __post_init__(self):
        if self.detection_counts is None:
            self.detection_counts = {
                "password": 0,
                "notice": 0,
                "team_select": 0,
            }
    
    def increment_count(self, screen_name: str) -> None:
        """특정 화면의 감지 시도 횟수를 증가시킵니다."""
        if screen_name in self.detection_counts:
            self.detection_counts[screen_name] += 1

    def get_count(self, screen_name: str) -> int:
        """특정 화면의 감지 시도 횟수를 반환합니다."""
        return self.detection_counts.get(screen_name, 0)

    def reset_count(self, screen_name: str) -> None:
        """특정 화면의 감지 시도 횟수를 초기화합니다."""
        if screen_name in self.detection_counts:
            self.detection_counts[screen_name] = 0

    def reset_all(self) -> None:
        """모든 상태를 초기화합니다."""
        self.password_passed = False
        self.notice_passed = False
        self.team_select_passed = False
        
        for key in self.detection_counts:
            self.detection_counts[key] = 0
