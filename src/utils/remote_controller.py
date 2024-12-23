import time
from .input_controller import InputController
from src.dao.remote_pcs_dao import RemoteDao
from database import get_db_context
from pywinauto import Desktop

class RemoteController:
    """원격 프로그램 제어를 위한 클래스"""
    
    WINDOW_TITLE = "멀티 원격관리 프로그램 Rimo"
    REMOTE_TOGGLE_KEY = '`'  # 원격 프로그램 시작/종료 키

    def __init__(self):
        """RemoteController 초기화"""
        self.input = InputController()
        self.remote_pcs_dao = RemoteDao()

    
    def _move_to_first_pc(self):
        """커서를 첫 번째 PC 위치로 이동"""
        for _ in range(4):  # 왼쪽으로 4번 이동하여 처음 위치로
            self.input.press_key('left')
    
    def _select_pc_by_number(self, pc_num: int):
        """PC 번호에 따라 커서 이동
        
        Args:
            pc_num (int): 선택할 PC 번호 (1부터 시작)
        """
        if pc_num == 1:
            self.input.press_key('right')
            self.input.press_key('left')
        else:
            for _ in range(pc_num - 1):
                self.input.press_key('right')

    async def select_remote(self):
        """원격 프로그램 창을 찾아 활성화"""
        try:
            desktop = Desktop(backend="uia")
            window = desktop.window(title_re=self.WINDOW_TITLE)
            
            if not window.exists():
                raise Exception("원격 프로그램 창을 찾을 수 없습니다.")
            
            window.restore()
            window.set_focus()
            return True
            
        except Exception as e:
            print(f"원격 프로그램 창 선택 중 오류 발생: {e}")
            return False
    
    
    async def start_remote(self, worker_id:str = None):
        """원격 프로그램 실행
        
        Args:
            worker_id (str): 작업자의 고유 ID
            
        Returns:
            bool: 실행 성공 여부
        """
        try:
            # PC 번호 가져오기
            if worker_id != None:
                async with get_db_context() as db:
                    pc_num = await self.remote_pcs_dao.get_pc_num_by_worker_id(db, worker_id)

            if not pc_num:
                print(f"원격 PC 정보가 존재하지 않습니다. (worker_id={worker_id})")
                return False
            
            # 원격 프로그램 창 선택
            if not await self.select_remote():
                return False
                
            # 커서 초기 위치로 이동
            self.input.press_key('right')  # 활성화를 위한 이동
            self._move_to_first_pc()
            
            # PC 선택
            self._select_pc_by_number(pc_num)
            
            # 원격 연결 시작
            self.input.press_key(self.REMOTE_TOGGLE_KEY)
            # print(f"PC {pc_num}번 원격 연결 시작...")
            return True
            
        except Exception as e:
            print(f"원격 프로그램 실행 중 오류 발생: {e}")
            return False

    async def exit_remote(self):
        """원격 프로그램 종료
        
        Returns:
            bool: 종료 성공 여부
        """
        try:
            self.input.press_key(self.REMOTE_TOGGLE_KEY)
            print("원격 연결 종료")
            return True
            
        except Exception as e:
            print(f"원격 프로그램 종료 중 오류 발생: {e}")
            return False


    async def exit_program(self):
        """ 프로그램 종료
        
        Returns:
            bool: 종료 성공 여부
        """
        try:
            print('test')
            self.input.press_key('win')
            time.sleep(1)
            self.input.press_key('win')
            time.sleep(1)
            self.input.hotkey('win', 'r')
            print("검색창")
            time.sleep(1)

            self.input.type_text('cmd')
            self.input.press_key('enter')
            print("cmd창 연결")
            time.sleep(1)
            self.input.type_text('taskkill /IM fczf.exe  /F')
            self.input.press_key('enter')
            print("fczf 프로그램 종료")
            time.sleep(1)
            # self.input.type_text('taskkill /IM fclauncher.exe /F')
            # self.input.press_key('enter')
            # print("fclauncher 프로그램 종료")
            # time.sleep(1)
            # self.input.type_text('taskkill /IM cefproczf.exe /F')
            # self.input.press_key('enter')
            # print("cefproczf 프로그램 종료")
            # time.sleep(1)
            self.input.type_text('exit')
            self.input.press_key('enter')
            print("프로그램 종료")
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"원격 프로그램 종료 중 오류 발생: {e}")
            return False