import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from example_interfaces.action import Fibonacci


ACTION_NAME = "/pat/execute_task"

ORDER_PICK = 400
ORDER_DEFECTIVE = 300


class ExecuteTaskClient(Node):
    def __init__(self):
        super().__init__("execute_task_client")

        self.client = ActionClient(
            self,
            Fibonacci,
            ACTION_NAME
        )

    def send_order(self, order: int) -> bool:
        goal_msg = Fibonacci.Goal()
        goal_msg.order = int(order)

        print(f"\n[CLIENT] 서버 대기 중: {ACTION_NAME}")
        self.client.wait_for_server()

        print(f"[CLIENT] Goal 전송: order={order}")

        send_goal_future = self.client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if goal_handle is None:
            print("[CLIENT] Goal 전송 실패")
            return False

        if not goal_handle.accepted:
            print("[CLIENT] Goal 거절됨")
            return False

        print("[CLIENT] Goal 수락됨")

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result_response = result_future.result()

        if result_response is None:
            print("[CLIENT] Result 수신 실패")
            return False

        result = result_response.result
        status = result_response.status

        print(f"[CLIENT] Result status = {status}")
        print(f"[CLIENT] Result sequence = {list(result.sequence)}")

        if len(result.sequence) >= 1 and result.sequence[0] == 1:
            print("[CLIENT] 작업 성공")
            return True

        print("[CLIENT] 작업 실패")
        return False

    def feedback_callback(self, feedback_msg):
        data = list(feedback_msg.feedback.sequence)

        status_names = {
            1: "pick",
            9: "finish",
        }

        if len(data) >= 1:
            code = data[0]
            message = status_names.get(code, f"unknown({code})")
            print(f"[FEEDBACK] {message}")


def input_floor_slot():
    floor = input("층 입력 1~3: ").strip()
    slot = input("칸 입력 1~6: ").strip()

    if floor not in ["1", "2", "3"]:
        print("[ERROR] 층은 1~3만 가능")
        return None

    if slot not in ["1", "2", "3", "4", "5", "6"]:
        print("[ERROR] 칸은 1~6만 가능")
        return None

    return floor, slot


def ask_confirm(message: str) -> bool:
    print(f"\n[확인] {message}")
    confirm = input("실행할까요? (y/n): ").strip().lower()
    return confirm == "y"


def make_place_order(floor: str, slot: str) -> int:
    return int("1" + floor + slot)


def make_retrieve_order(floor: str, slot: str) -> int:
    return int("2" + floor + slot)


def run_after_pick_menu(node: ExecuteTaskClient):
    while True:
        print("\n==============================")
        print("픽 완료 후 작업 선택")
        print("1: 적재")
        print("2: 불량품 처리")
        print("b: 초기 메뉴로 돌아가기")
        print("==============================")

        selected = input("작업 선택: ").strip().lower()

        if selected == "b":
            print("초기 메뉴로 돌아갑니다.")
            return

        if selected == "1":
            position = input_floor_slot()
            if position is None:
                continue

            floor, slot = position
            order = make_place_order(floor, slot)

            if not ask_confirm(f"적재를 실행합니다. order={order}"):
                print("적재 취소")
                continue

            node.send_order(order)
            return

        if selected == "2":
            order = ORDER_DEFECTIVE

            if not ask_confirm(f"불량품 처리를 실행합니다. order={order}"):
                print("불량품 처리 취소")
                continue

            node.send_order(order)
            return

        print("[ERROR] 1, 2, b 중 하나만 입력")


def run_main_menu(node: ExecuteTaskClient):
    while True:
        print("\n==============================")
        print("초기 메뉴")
        print("1: 픽")
        print("2: 출고")
        print("q: 종료")
        print("==============================")

        selected = input("선택: ").strip().lower()

        if selected == "q":
            print("종료")
            return

        if selected == "1":
            if not ask_confirm("픽을 실행합니다."):
                print("픽 취소")
                continue

            pick_success = node.send_order(ORDER_PICK)

            if not pick_success:
                print("[ERROR] 픽 실패. 초기 메뉴로 돌아갑니다.")
                continue

            run_after_pick_menu(node)
            continue

        if selected == "2":
            position = input_floor_slot()
            if position is None:
                continue

            floor, slot = position
            order = make_retrieve_order(floor, slot)

            if not ask_confirm(f"출고를 실행합니다. order={order}"):
                print("출고 취소")
                continue

            node.send_order(order)
            continue

        print("[ERROR] 1, 2, q 중 하나만 입력")


def main():
    rclpy.init()
    node = ExecuteTaskClient()

    try:
        run_main_menu(node)

    except KeyboardInterrupt:
        print("\n강제 종료")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
