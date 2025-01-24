from pymysqlreplication.row_event import (
    UpdateRowsEvent,
)
from sqlalchemy.orm import context, remote
from src.controller.ten_min_controller import do_task
from src import state
from src.dao.remote_pcs_dao import RemoteDao
from database import get_db_context
from src.utils import error_handler
from src.utils.error_handler import ControllerError, ErrorHandler

error_handler = ErrorHandler()

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
                        before_values = {table_columns[i]: before_values.get(unknown_cols[i], None) for i in range(len(table_columns))}
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
                        state.add_worker(worker_id)
                        
                        # 작업 상태 업데이트
                        async with get_db_context() as db:
                            await RemoteDao().update_tasks_request(db, server_id, worker_id, "idle")

                    elif table_name == "daenak":
                        # ten_min 테이블의 컬럼 매핑
                        ten_min_columns = ["id", "name", "depositor", "service", "game_id", "pw1", "pw2", "nickname", "phone", "login_type", 
                                            "price", "otp", "instant", "topclass", "coupon_count", "coupon_content", "state", "cookie", "regdate", "deposit_date",
                                            "success_date", "worker_id", "erased_worker_id", "erased_reason", "erased_date", "path", "same_name",
                                            "is_waiting_active", "topclass_agree", "otp_pass"]

                        unknown_cols = []
                        for i in range(len(ten_min_columns)):
                            unknown_cols.append(f"UNKNOWN_COL{i}")

                        before_values = {ten_min_columns[i]: before_values.get(unknown_cols[i], None) for i in range(len(ten_min_columns))}
                        after_values = {ten_min_columns[i]: after_values.get(unknown_cols[i], None) for i in range(len(ten_min_columns))}

                        worker_id = after_values.get("worker_id")
                        print(f"worker_id={worker_id}, state.worker_id={state.worker_id}")
                        if not worker_id or worker_id is None or not worker_id in state.worker_id:
                            continue

                        # otp_pass에 관한 update사항이라면 continue를 통해 로직에서 빠져나오기
                        if after_values.get("otp_pass") != before_values.get("otp_pass"):
                            print(f"before_values.get('otp_pass')={before_values.get('otp_pass')}, after_values.get('otp_pass')={after_values.get('otp_pass')}")
                            continue


                        # ten_min 테이블의 필요한 값들 가져오기
                        deanak_id = after_values.get("id")
                        service = after_values.get("service")
                        pw2 = after_values.get("pw2")
                        otp = after_values.get("otp")
                        otp_pass = after_values.get("otp_pass")
                        coupon_count = after_values.get("coupon_count")
                        ten_min_state = after_values.get("state")

                        # print(f"개별 row 처리: service={service}, worker_id={worker_id}, pw2={pw2}, coupon_count={coupon_count}, otp={otp}, ten_min_state={ten_min_state}, otp_pass={otp_pass}")

                        ten_min_info = {
                            "deanak_id": deanak_id,
                            "worker_id": worker_id,
                            "service": service,
                            "pw2": pw2,
                            "otp": otp,
                            "otp_pass": otp_pass,
                            "coupon_count": coupon_count,
                            "ten_min_state": ten_min_state,
                        }
                        context = {"deanak_id": deanak_id, "worker_id": worker_id}

                        # 서비스 실행
                        if service == "10분접속" and otp == 0 and coupon_count == 0 and ten_min_state == '2':
                            remote_pcs = await check_remote_pc_state(server_id, worker_id, ten_min_info)
                            if not remote_pcs:
                                continue

                            print("otp 작업 없이 10분 접속 작업 시작")
                            await do_task("ten_min_start", ten_min_info)

                        if service == "10분접속" and otp == 1 and otp_pass == 0 and coupon_count == 0 and ten_min_state == '2':
                            remote_pcs = await check_remote_pc_state(server_id, worker_id, ten_min_info)
                            if not remote_pcs:
                                continue

                            print("otp 인식 시작")
                            await do_task("otp_check", ten_min_info)

            except ControllerError as e:
                async with get_db_context() as db:
                    await RemoteDao.update_tasks_request(db, server_id, "stopped")
                error_handler.handle_error(e, critical=True, context=context, user_message=error_handler.CONTROLLER_ERROR)
                print(f"deanak_controller.py파일 내의 do_task함수에서 알수 없는 오류 발생: {e}")
                continue
            except Exception as e:
                async with get_db_context() as db:
                    await RemoteDao.update_tasks_request(db, server_id, "stopped")
                error_handler.handle_error(e, critical=True, context=context, user_message=error_handler.HANDLER_ERROR)
                print(f"개별 row 처리 중 오류 발생: {e}")
                continue

    except Exception as e:
        async with get_db_context() as db:
            await RemoteDao.update_tasks_request(db, server_id, "stopped")
        error_handler.handle_error(e, critical=True, context=context, user_message=error_handler.HANDLER_ERROR)
        print(f"전체 이벤트 처리 중 오류 발생: {e}")
        raise e

async def check_remote_pc_state(server_id, worker_id, ten_min_info):
    """원격 PC의 상태를 확인하고 필요한 경우 대기열에 추가"""
    async with get_db_context() as db:
        remote_pcs = await RemoteDao.get_remote_pc_by_server_id_and_worker_id(db, server_id, worker_id)
        if remote_pcs is None:
            print(f"해당 작업자의 원격pc 서버를 찾지 못했습니다.")
            return False

        working_count = await RemoteDao.get_working_count_by_server_id(db, server_id)
        worker_remote_data = await RemoteDao.get_remote_pc_by_server_id_and_worker_id(db, server_id, worker_id) 
        if working_count > 0 or worker_remote_data.state == "waiting":
            print(f"작업 중인 PC가 있습니다. 요청을 대기열에 추가합니다: worker_id={worker_id}")
            service_request = {
                'request': "deanak_start",
                'ten_min_info': ten_min_info,
                'worker_id': worker_id
            }
            await state.pending_services.put(service_request)
            return False
        
        return remote_pcs