import uuid
import os
import asyncio
from asyncio import Queue
from datetime import datetime

class unique_id:
    def __init__(self):
        self.file_path = "unique_id.txt"
        
    async def generate_unique_id(self):
        """고유 ID를 생성하고 파일에 저장"""
        now = datetime.now()
        date_part = now.strftime("%H%M%S")
        random_part = str(int(uuid.uuid4().int % 100000)).zfill(5)
        unique_id = int(date_part + random_part)
        try:
            with open(self.file_path, 'w') as f:
                f.write(str(unique_id))
            return unique_id
        except Exception as e:
            print(f"고유 ID 생성 중 오류 발생: {e}")
            return None

    async def read_unique_id(self):
        """파일에서 고유 ID 읽기"""
        try:
            with open(self.file_path, 'r') as f:
                return int(f.read().strip())
        except Exception as e:
            print(f"고유 ID 읽기 중 오류 발생: {e}")
            return None

    async def delete_unique_id(self):
        """고유 ID 파일을 삭제하고 ID 반환"""
        try:
            with open(self.file_path, 'r') as f:
                unique_id = int(f.read().strip())
            os.remove(self.file_path)
            return unique_id
        except Exception as e:
            print(f"고유 ID 삭제 중 오류 발생: {e}")
            return None

# 태스크 관리를 위한 전역 변수
monitoring_task = None
service_running_task = None
waiting_process_task = None
is_running = True  # Task 실행 상태를 제어하기 위한 플래그
worker_id = []
SERVICE_TIMER = 1 * 35 # 시간분으로 11분
pending_services = Queue()

def add_worker(worker_id_value):
    """worker_id 추가"""
    if worker_id_value not in worker_id:
        worker_id.append(worker_id_value)

def remove_worker(worker_id_value):
    """worker_id 제거"""
    if worker_id_value in worker_id:
        worker_id.remove(worker_id_value)