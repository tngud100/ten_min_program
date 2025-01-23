import ast
from dotenv import load_dotenv
import os
import asyncio
import aiohttp


class Api:
    def __init__(self):
        load_dotenv()
        self.url = os.getenv("API_URL");
        self.error_handler = None

    async def _make_request(self, method, url, **kwargs):
        """공통 API 요청 함수"""
        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with getattr(session, method)(url, **kwargs) as response:
                        if response.status != 200:
                            error_content = await response.text()
                            content_type = response.headers.get('Content-Type', '')
                            print(f"API 호출 실패: 상태 코드 {response.status}")
                            print(f"Content-Type: {content_type}")
                            print(f"응답 내용: {error_content}")
                            return False, None
                        
                        try:
                            response_data = await response.json()
                            print(f"response_data : {response_data}")
                            return True, response_data
                        except aiohttp.ContentTypeError:
                            # print("API 응답이 JSON 형식이 아닙니다")
                            return True, None

            except aiohttp.ClientError as e:
                if "WinError 64" in str(e):
                    print(f"네트워크 연결 끊김 감지 (시도 {attempt + 1}/{max_retries})")
                else:
                    print(f"API 호출 중 네트워크 오류 발생 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                    continue
                return False, None
                
            except Exception as e:
                print(f"API 호출 중 예상치 못한 오류 발생: {str(e)}")
                return False, None

    # 대낙 완료
    async def send_complete(self, deanak_id):
        url = f"{self.url}/success/{deanak_id}"
        print(f"Sending complete request to URL: {url}")
        success, _ = await self._make_request('post', url)
        if success:
            print("대낙 완료 API 호출 완료")
        return success

    # 오류 발생
    async def send_error(self, deanak_id, error_text, detail):
        params = {'reason': error_text, 'detail': detail}
        url = f"{self.url}/error/{deanak_id}"
        print(f"Sending error request to URL: {url}")
        print(f"Parameters: {params}")
        success, _ = await self._make_request('post', url, params=params)
        if success:
            print("에러 메시지 전송 완료")
        return success

    # OTP 전송
    async def send_otp(self, deanak_id, otp_text):
        params = {'otp': otp_text}
        url = f"{self.url}/otp/{deanak_id}"
        print(f"Sending OTP request to URL: {url}")
        print(f"Parameters: {params}")
        success, _ = await self._make_request('post', url, params=params)
        if success:
            print("OTP 전송 완료")
        return success
    
    # 서버 실행
    async def send_login(self, server_id):
        params = {'uuid': server_id}
        url = f"{self.url}/login"
        print(f"Sending start request to URL: {url}")
        print(f"Parameters: {params}")
        success, _ = await self._make_request('post', url, params=params)
        if success:
            print("서버 실행 완료")
        return success
        
    # 서버 종료
    async def send_disconnect(self, server_id):
        url = f"{self.url}/disconnection/{server_id}"
        print(f"Sending disconnect request to URL: {url}")
        success, _ = await self._make_request('post', url)
        if success:
            print("서버 종료 완료")
        return success

    # 해당 서버의 작업자 작업 시작
    async def send_start(self, deanak_id):
        url = f"{self.url}/start/{deanak_id}"
        print(f"Sending start request to URL: {url}")
        success, _ = await self._make_request('post', url)
        if success:
            print("작업 시작 완료")
        return success

    # 해당 서버의 작업자 작업 종료
    async def send_success(self, deanak_id):
        url = f"{self.url}/success/{deanak_id}"
        print(f"Sending success request to URL: {url}")
        success, _ = await self._make_request('post', url)
        if success:
            print("작업 종료 완료")
        return success

    # 해당 서버의 작업자 대기
    async def send_waiting(self, deanak_id):
        url = f"{self.url}/waiting/{deanak_id}"
        print(f"Sending waiting request to URL: {url}")
        success, _ = await self._make_request('post', url)
        if success:
            print("작업 대기 완료")
        return success