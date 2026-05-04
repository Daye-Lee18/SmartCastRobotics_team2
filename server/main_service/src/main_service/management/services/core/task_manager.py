
from __future__ import annotations

from typing import Protocol, runtime_checkable, List
from contracts.models import *

from services.legacy.task_manager import (

StartProductionResult,

TaskManager as LegacyTaskManager,

TaskManagerError,

)
from services.core.contracts.protocols import ITaskManager



class TaskManager(LegacyTaskManager,ITaskManager):
    MAX_COL = 6
    
    def __init__(self, sm):
        self.sm = sm
        self.order_start_configs = {}#오더별로 할당된 적재 기준 위치
        #self.order_assigned_counts = {}#오더별로 할당된 양품 개수를 관리

        
    #오더 투입시 해당 오더가 사용할 적재 공간 예약
    def reserve_rack_slots(self, order_id: int, start_pos: str):
        """주문 투입 시 해당 오더가 사용할 슬롯들을 물리적 구조(6칸)에 맞춰 예약"""
        row, col = map(int, start_pos.split('-'))
        target_qty = self.sm.orders[order_id]["target"]
        
        assigned = 0
        # 시작 위치를 절대 인덱스로 변환 (예: 1-1은 0, 1-6은 5, 2-1은 6)
        current_abs_idx = (row - 1) * self.MAX_COL + (col - 1)
        
        while assigned < target_qty:
            # 절대 인덱스를 다시 row-col 좌표로 변환 (핵심 수정)
            curr_row = (current_abs_idx // self.MAX_COL) + 1
            curr_col = (current_abs_idx % self.MAX_COL) + 1
            
            pos_key = (curr_row, curr_col)
            
            if pos_key in self.sm.slot_table:
                self.sm.slot_table[pos_key]["order_id"] = order_id
                assigned += 1
            else:
                # 랙의 물리적 범위를 벗어난 경우 (예: 3층 6칸을 넘어감)
                print(f"[경고] 랙 공간 부족: {curr_row}-{curr_col} 위치가 slot_table에 없음")
                break
            
            current_abs_idx += 1 # 다음 절대 칸으로 이동

        print(f"[설정] 주문 {order_id} 구역 예약 완료")

    #오더 종료시 오더 적재기준 위치 메모리 해제
    def remove_order_reserve(self, order_id: int):
        """주문이 완전히 종료되면 호출하여 메모리 해제"""
        if order_id in self.order_start_configs:
            del self.order_start_configs[order_id]
            print(f"[삭제] 주문 {order_id} 설정이 메모리에서 제거되었습니다.")

    #오더 종료 시 Empty 슬롯의 소유권 해제 (Occupied는 유지 - 출고용)
    def remove_order_config(self, order_id: int):
       
        for (f, c), data in self.sm.slot_table.items():
            if data["order_id"] == order_id:
                if data["status"] in ["Empty", "Reserved"]:
                    data["order_id"] = None
                    data["status"] = "Empty"

    #작업 객체 생성 to orchestrator
    def create_next_task(self, item_info: ItemStatusRecord, event: str = None) -> List[NextTaskResult]:
        
        # [B] 일반적인 공정 흐름 (자동 전이)
        # 특별한 외부 조건이 없어도 순서에 따라 다음 작업을 자동으로 뱉어줍니다.
        #none -> MM -> pour -> dm     -> pp -> toInsp -> Insp ->toWaitPa ->pa gp/dp
        #                ㄴ> topp    _|     ㄴ>toStgr                   _|
        print(f"[DATA INPUT] orchestrator에서 create_next_task 호출 발생 : item_ifo {item_info} event {event} ") 

        flow_map = {
            # MM이 끝나면 자동으로 POUR로 넘어감
            TaskType.MM: TaskType.POUR,      
            
            # DM(탈형)이 끝나면 자동으로 PP(가공)로 넘어감
            TaskType.DM: TaskType.PP,        
            
            # PP가 끝나면 자동으로 두 장소로 이송 시작
            TaskType.PP: [TaskType.ToINSP, TaskType.ToSTRG], 
            
            # 이송(ToINSP)이 끝나면 자동으로 INSP(검사) 시작
            TaskType.ToINSP: TaskType.INSP,
        }
        
        task_results = []
        
        # [1] 이벤트 기반 특수 공정 분기 (최우선 처리)
        # 이벤트가 들어오면 last_task_type에 상관없이 즉시 해당 로직을 타고 return합니다.
        if event:
            if event == "pour":
                task_results.append(self._create_result(item_info, TaskType.ToPP))
                return task_results

            elif event == "topp":
                task_results.append(self._create_result(item_info, TaskType.DM))
                return task_results

            elif event == "tostrg":
                task_results.append(self._create_result(item_info, TaskType.ToWaitPA))
                return task_results

            elif event == "tostrg_DLD":
                if item_info.is_defective:
                    # 1. 불량 보충 아이템 생성 및 MM 태스크 발행 (우선순위 10)
                    replacement_id = self.sm.create_empty_item(item_info.order_id)
                    task_results.append(NextTaskResult(
                        item_id=replacement_id, 
                        txn_id=self.sm.insert_task_txn(CreateTaskInput(item_id=replacement_id, task_type=TaskType.MM)), 
                        task_type=TaskType.MM, 
                        priority=10
                    ))

                    # 2. [Slot Table 반영] 현재 불량 제품이 예약했던 슬롯을 다시 Empty로 변경
                    # item_info 혹은 현재 할당된 slot_table에서 'Reserved' 상태인 내 칸을 찾아 해제합니다.
                    for (f, c), data in self.sm.slot_table.items():
                        if data["order_id"] == item_info.order_id and data["status"] == "Reserved":
                            data["status"] = "Empty"  # 소유권(order_id)은 유지, 상태만 초기화
                            print(f"[슬롯] 불량 발생으로 인한 슬롯 {f}-{c} 복구 (오더 {item_info.order_id} 전용)")
                            break

                    # 3. 불량품 배출(PA_DP) 태스크 추가
                    task_results.append(self._create_result(item_info, TaskType.PA_DP))
                
                else:
                    # 양품일 경우 정상 적재(PA_GP) 진행
                    # (이후 Orchestrator에서 PA_GP 완료 시 'Occupied'로 변경 처리)
                    task_results.append(self._create_result(item_info, TaskType.PA_GP))
                
                return task_results

        # [2] 상태 기반 흐름 제어 및 가드 (이벤트가 없을 때 실행)
        # 최초 투입 (신규 MM)
        if item_info.last_task_type is None:
            res = self._create_result(item_info, TaskType.MM)
            res.priority = 0  # 신규 투입은 가장 낮은 우선순위
            task_results.append(res)
            return task_results

        # 특정 공정 완료 후 다음 이벤트 대기를 위해 흐름을 끊는 구간
        stop_states = [TaskType.POUR, TaskType.INSP, TaskType.ToWaitPA]
        if item_info.last_task_type in stop_states:
            return []

        
        next_type = flow_map.get(item_info.last_task_type)
        if next_type:
            if isinstance(next_type, list):
                for t in next_type:
                    task_results.append(self._create_result(item_info, t))
            else:
                task_results.append(self._create_result(item_info, next_type))

        return task_results
    
    # txn 생성 to state manager
    def _create_result(self, item_info, task_type):  #현재 진행된 아이템 정보 , 다은 공정 이름
        # 트랜잭션 DB 기록 로직 (sm.insert_task_txn 호출 등) 포함
        rack_pos = self._calculate_rack_pos(task_type, item_info) #
        curr_input = CreateTaskInput(item_id=item_info.item_id, task_type=task_type, rack_pos=rack_pos , txn_stat=TxnStat.QUE)
        curr_txn_id = self.sm.insert_task_txn(curr_input)

    
        return NextTaskResult(item_id=item_info.item_id, txn_id=curr_txn_id, task_type=task_type , rack_pos=rack_pos) #proority = 0 
    
    
    #적재위치계산 
    def _calculate_rack_pos(self, task_type: TaskType, item_info: ItemStatusRecord) -> Optional[str]:
        if item_info.is_defective:
            return "DEFECTIVE_ZONE"
        
        if task_type == TaskType.ToWaitPA:
            # slot_table을 순회할 때 row, col 순서로 정렬하여 가장 빠른 칸을 찾음
            sorted_slots = sorted(self.sm.slot_table.items()) 
            for (f, c), data in sorted_slots:
                # 1-7 같은 값이 절대 나올 수 없도록 필터링 가능
                if c > self.MAX_COL: 
                    continue 

                if data["order_id"] == item_info.order_id and data["status"] == "Empty":
                    data["status"] = "Reserved"
                    return f"{f}-{c}"
        return None
    
