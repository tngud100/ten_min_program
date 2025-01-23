from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
from config.settings import DB_CONFIG
from .handler import handle_row_event
import asyncio
from src import state

async def monitor_binlog(unique_id_value):
    """Binlog 모니터링 로직"""
    state.monitoring_task = asyncio.current_task()

    stream = BinLogStreamReader(
        connection_settings=DB_CONFIG,
        server_id=1,
        blocking=False,
        resume_stream=True,
        only_events=[UpdateRowsEvent],
        only_tables=["remote_pcs", "daenak"],
        only_schemas=["ez_daenak"],
        freeze_schema=False # 스키마 변경사항을 실시간으로 반영하여 컬럼명이 제대로 표시되도록 함
    )

    print("Binlog 모니터링 시작")    
    while not state.monitoring_task.cancelled():  # 취소 여부 확인
        try:
            binlogevent = stream.fetchone()
            if binlogevent is None:
                await asyncio.sleep(1)  # CPU 사용률 조절을 위한 짧은 대기
                continue

            if isinstance(binlogevent, (UpdateRowsEvent)):
                await handle_row_event(binlogevent, unique_id_value)
                
        except Exception as e:
            if not state.monitoring_task.cancelled():  # 취소가 아닌 실제 오류인 경우만 출력
                # print(f"Binlog 이벤트 처리 중 오류 발생: {e}")
                await asyncio.sleep(3)  # 오류 발생시 5초 대기
            continue
        finally:
            if 'stream' in locals():
                stream.close()
