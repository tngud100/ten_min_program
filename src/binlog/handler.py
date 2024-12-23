from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
from src.controller.ten_min_controller import do_task
from src import state
from src.dao.remote_pcs_dao import RemoteDao
from database import get_db_context

async def handle_row_event(event, server_id):
    """이벤트 처리 로직"""
    try:
        table_columns = ["id", "server_id", "service", "worker_id", "state", "server_online_time"]
        for row in event.rows:
            try:
                # remote_pcs테이블에서 after_values의 server_id와 인자로 받은 server_id가 같고 worker_id가 있을때 
                # ten_min테이블에서 service가 일반대낙, otp가 0이며, coupon_count가 0이고, state가 2이면서, worker_id가 존재하면 자동 대낙 실행
                before_values = row.get("before_values", {})
                after_values = row.get("after_values", {})

                # 이벤트가 remote_pcs의 변경인지 ten_min의 변경인지 확인
                table_name = event.table
                if isinstance(event, (UpdateRowsEvent)):
                    if table_name == "remote_pcs":

                        # UNKNOWN_COL을 실제 컬럼 이름으로 매핑
                        table_columns = ["id", "server_id", "service", "worker_id", "state", "server_online_time"]
                        unknown_cols = ["UNKNOWN_COL0", "UNKNOWN_COL1", "UNKNOWN_COL2", "UNKNOWN_COL3", "UNKNOWN_COL4", "UNKNOWN_COL5"]

                        # UNKNOWN_COL을 실제 컬럼 이름으로 변경
                        after_values = {table_columns[i]: after_values.get(unknown_cols[i], None) for i in range(len(table_columns))}

                        # server_id 검증
                        if "server_id" in after_values and str(after_values["server_id"]) != str(server_id):
                            continue
                        worker_id = after_values.get("worker_id")

                        if worker_id is None:
                            print("worker_id이 없음")
                            continue

                        # 상태가 변경되었다면 스킵
                        if str(after_values.get("state")) != str(before_values.get("state")):
                            print(f"상태가 변경되었음: {before_values.get('state')} -> {after_values.get('state')}")
                            continue

                        if worker_id in state.worker_id:
                            print(f"해당 worker_id가 이미 존재: {worker_id}")
                            continue

                        print(f"worker_id데이터 state에 삽입")
                        state.worker_id.append(worker_id)
                        
                        # 작업 상태 업데이트
                        async with get_db_context() as db:
                            await RemoteDao().update_tasks_request(db, server_id, worker_id, "idle")

                    elif table_name == "deanak":
                        # ten_min 테이블의 컬럼 매핑
                        ten_min_columns = ["id", "service", "pw2", "worker_id", "coupon_count", "otp", "state"]
                        unknown_cols = ["UNKNOWN_COL0", "UNKNOWN_COL1", "UNKNOWN_COL2", "UNKNOWN_COL3", "UNKNOWN_COL4", "UNKNOWN_COL5", "UNKNOWN_COL6"]

                        after_values = {ten_min_columns[i]: after_values.get(unknown_cols[i], None) for i in range(len(ten_min_columns))}

                        worker_id = after_values.get("worker_id")
                        print(f"worker_id={worker_id}, state.worker_id={state.worker_id}")
                        if not worker_id or worker_id is None or not worker_id in state.worker_id:
                            continue

                        # ten_min 테이블의 필요한 값들 가져오기
                        deanak_id = after_values.get("id")
                        service = after_values.get("service")
                        pw2 = after_values.get("pw2")
                        otp = after_values.get("otp")
                        coupon_count = after_values.get("coupon_count")
                        ten_min_state = after_values.get("state")

                        print(f"개별 row 처리: service={service}, worker_id={worker_id}, pw2={pw2}, coupon_count={coupon_count}, otp={otp}, ten_min_state={ten_min_state}")

                        ten_min_info = {
                            "deanak_id": deanak_id,
                            "worker_id": worker_id,
                            "service": service,
                            "pw2": pw2,
                            "coupon_count": coupon_count,
                            "otp": otp,
                            "ten_min_state": ten_min_state,
                        }

                        # 원격pc의 state가져오기
                        async with get_db_context() as db:
                            remote_pcs = await RemoteDao.get_remote_pc_by_server_id_and_worker_id(db, server_id, worker_id)
                            # print(f"remote_pcs={remote_pcs}")
                            if remote_pcs is None:
                                print(f"해당 작업자의 원격pc 서버를 찾지 못했습니다.")
                                continue

                        if service == "10분접속" and otp == 0 and coupon_count == 0 and ten_min_state == 2 and worker_id is not None and remote_pcs.state == "idle":
                            print("자동 10분접속 실행")
                            await do_task("ten_min_start", ten_min_info=ten_min_info)
                    
            except Exception as e:
                print(f"개별 row 처리 중 오류 발생: {e}")
                continue
                
    except Exception as e:
        print(f"전체 이벤트 처리 중 오류 발생: {e}")
        raise
