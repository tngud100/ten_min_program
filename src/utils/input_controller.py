import pyautogui
import keyboard
import time

class InputController:
    def __init__(self):
        pyautogui.FAILSAFE = True
        self.default_delay = 0.1

    def click(self, x, y, clicks=1):
        """마우스 클릭"""
        try:
            pyautogui.click(x=x, y=y, clicks=clicks)
            time.sleep(self.default_delay)
            return True
        except Exception as e:
            print(f"마우스 클릭 중 오류 발생: {e}")
            return False

    def cursor_move(self, x, y):
        """마우스 이동"""
        try:
            pyautogui.moveTo(x, y)
            time.sleep(self.default_delay)
            return True
        except Exception as e:
            print(f"마우스 이동 중 오류 발생: {e}")
            return False

    def press_key(self, key):
        """키 입력"""
        try:
            keyboard.press_and_release(key)
            time.sleep(self.default_delay)
            return True
        except Exception as e:
            print(f"키 입력 중 오류 발생: {e}")
            return False

    def hotkey(self, *args):
        """단축키 입력"""
        try:
            # 모든 키를 누름
            for key in args:
                keyboard.press(key)
                time.sleep(0.1)  # 각 키 입력 사이에 약간의 딜레이
            
            # 역순으로 키를 뗌
            for key in reversed(args):
                keyboard.release(key)
                time.sleep(0.1)
            
            time.sleep(self.default_delay)
            return True
        except Exception as e:
            print(f"단축키 입력 중 오류 발생: {e}")
            # 에러 발생 시 모든 키를 떼줌
            for key in args:
                try:
                    keyboard.release(key)
                except:
                    pass
            return False

    def type_text(self, text):
        """텍스트 입력"""
        try:
            pyautogui.typewrite(text, interval=0.05)
            time.sleep(self.default_delay)
            return True
        except Exception as e:
            print(f"텍스트 입력 중 오류 발생: {e}")
            return False