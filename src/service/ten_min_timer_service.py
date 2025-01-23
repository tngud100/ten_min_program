from datetime import datetime
import asyncio
from os import error
from database import get_db_context
from src.dao.deanak_dao import DeanakDao
from src.utils import api
from src.utils.error_handler import ErrorHandler, CheckTimerError, CantFindTenMinDataError
from src.dao.auto_ten_min_dao import AutoTenMinDao
from src.dao.remote_pcs_dao import RemoteDao
from src.utils.remote_controller import RemoteController
from src.utils.input_controller import InputController
from src import state
from src.models.service_state import ServiceState
from src.utils.api import Api

class TenMinTimerService:
    """10분 접속 타이머 관리 서비스

    Attributes:
        remote (RemoteController): 원격 제어 컨트롤러
        error_handler (ErrorHandler): 에러 처리기
        remote_pcs_dao (RemoteDao): 원격 PC 데이터 접근 객체
        auto_ten_min_dao (AutoTenMinDao): 10분 접속 데이터 접근 객체
        deanak_dao (DeanakDao): 대낙 작업 데이터 접근 객체
        input_controller (InputController): 입력 제어 컨트롤러
        state (state): 전역 상태 관리 객체
    """
    def __init__(self, remote: RemoteController, error_handler: ErrorHandler, 
                 remote_pcs_dao: RemoteDao, auto_ten_min_dao: AutoTenMinDao, deanak_dao: DeanakDao,
                 input_controller: InputController, state: state, api: Api):
        self.remote = remote
        self.error_handler = error_handler
        self.remote_pcs_dao = remote_pcs_dao
        self.auto_ten_min_dao = auto_ten_min_dao
        self.deanak_dao = deanak_dao
        self.input_controller = input_controller
        self.state = state
        self.api = api

    async def check_timer(self, server_id: str, deanak_id: int):
        """10분 접속 타이머를 확인하고 상태를 업데이트합니다.

        Args:
            server_id (str): 서버 고유 ID
            deanak_id (int): 대낙 작업 고유 ID

        Returns:
            bool: 타이머 시작 성공 여부
        """
        try:
            async with get_db_context() as db:
                # 만료된 서비스 처리
                expired_services = await self.auto_ten_min_dao.get_expired_services(db)
                for service in expired_services:
                    await self.auto_ten_min_dao.update_ten_min_state(
                        db, service.deanak_id, service.server_id, 
                        ServiceState.TIMEOUT
                    )
                    print("시간 초과된 서비스 db업데이트")


                print("10분 접속 타이머 체크 완료")
                # 현재 서비스 상태 확인
                timer_data = await self.auto_ten_min_dao.find_auto_ten_min(db, deanak_id, server_id)
                if timer_data is None:
                    raise CantFindTenMinDataError("10분 접속 타이머 데이터를 찾을 수 없습니다.")
                
                if timer_data.state != ServiceState.TIMEOUT:
                    print(f"deanak_id:{deanak_id}, 10분 접속 타이머가 초과되지 않아 진행되지 않습니다.")
                    return False

                # 작업 중인 PC 수 확인
                working_count = await self.remote_pcs_dao.get_working_count_by_server_id(db, server_id)
                if working_count > 0:
                    print("작업 중인 PC가 있으므로 종료 로직은 이후 진행됩니다.")
                    return False  # 아직 다른 PC가 작업 중

                # 대기 큐 확인
                waiting_queue = await self.auto_ten_min_dao.get_waiting_queue_by_server_id(db, server_id)
                if not waiting_queue or waiting_queue[0].deanak_id != deanak_id:
                    print("대기 큐에 있는 deanak_id의 번호가 아니거나 없습니다.")
                    return False  # 이 PC가 큐의 첫 번째가 아님

                # 작업 시작
                worker_id = await self.deanak_dao.get_worker_id_by_deanak_id(db, deanak_id)
                await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "working")
                await self.auto_ten_min_dao.update_ten_min_state(db, deanak_id, server_id, ServiceState.WORKING)
                await self.api.send_start(deanak_id)

            return await self.finish_ten_min(server_id, deanak_id, worker_id)
        
        except  CantFindTenMinDataError as e:
            raise
        except (Exception, CheckTimerError) as e:
            raise CheckTimerError

    async def finish_ten_min(self, server_id: str, deanak_id: int, worker_id: str):
        """10분 접속을 종료하고 상태를 업데이트합니다.

        Args:
            server_id (str): 서버 고유 ID
            worker_id (str): 작업자 고유 ID

        Returns:
            bool: 종료 처리 성공 여부
        """
        # 원격 연결 시작
        try:
            async with get_db_context() as db:
                pc_num = await self.remote_pcs_dao.get_pc_num_by_worker_id(db, worker_id);
            
            if not await self.remote.start_remote(pc_num):
                return False

            # 프로그램 종료 (Alt+F4)
            await self.remote.exit_program()
            await asyncio.sleep(1)  # 종료 대기
            # 원격 연결 종료
            await self.remote.exit_remote()

            async with get_db_context() as db:
                # PC 상태를 idle로 변경
                await self.remote_pcs_dao.update_tasks_request(db, server_id, worker_id, "idle")
                # 10분 접속 상태 업데이트 (종료 시간 기록)
                await self.auto_ten_min_dao.update_ten_min_state(
                    db, deanak_id=deanak_id, server_id=server_id, 
                    state=ServiceState.TERMINATED,
                    end_waiting_time=datetime.now()
                )
                await self.api.send_success(deanak_id)
                
            return True

        except Exception as e:
            raise CheckTimerError(f"check_timer함수의 finish_ten_min함수 내 오류")

    async def process_waiting_tasks(self):
        """대기 중인 10분 접속 작업들을 처리"""
        try:
            async with get_db_context() as db:
                waiting_tasks = await self.auto_ten_min_dao.waiting_ten_min(db)

            print(f"대기 중인 작업 수: {len(waiting_tasks) if waiting_tasks else 0}")

            if waiting_tasks:
                for task in waiting_tasks:
                    print(f"대기 중인 작업 처리 - deanak_id: {task.deanak_id}")
                    await self.check_timer(task.server_id, task.deanak_id)
        
        except CantFindTenMinDataError as e:
            raise
        except (Exception, CheckTimerError) as e:
            raise CheckTimerError