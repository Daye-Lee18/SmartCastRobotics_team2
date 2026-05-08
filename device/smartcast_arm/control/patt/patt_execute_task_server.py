import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer

from example_interfaces.action import Fibonacci
from pymycobot.mycobot import MyCobot


PORT = "/dev/ttyUSB0"
BAUD = 1000000

_HOME = [90, 0, 0, 0, 0, 45]
_PICK = [90, -20.39, -36.56, -7.99, 0, 45]


class ExecuteTaskServer(Node):
    def __init__(self):
        super().__init__("execute_task_server")

        self.get_logger().info(f"Connecting myCobot: {PORT}, baud={BAUD}")
        self.mc = MyCobot(PORT, BAUD)
        time.sleep(2)

        angles = self.mc.get_angles()
        self.get_logger().info(f"Initial angles: {angles}")

        self._action_server = ActionServer(
            self,
            Fibonacci,
            "/pat/execute_task",
            self.execute_callback
        )

        self.get_logger().info("ExecuteTask Action Server started: /pat/execute_task")

    # ==============================
    # 기본 동작 함수
    # ==============================
    def _move(self, angles, speed=30, delay=1):
        self.get_logger().info(f"Move: {angles}, speed={speed}")
        self.mc.send_angles(angles, speed)
        time.sleep(delay)

    def _gripper_open(self):
        self.get_logger().info("Gripper open")
        self.mc.set_gripper_value(100, 50)
        time.sleep(1)

    def _gripper_close(self):
        self.get_logger().info("Gripper close")
        self.mc.set_gripper_value(0, 50)
        time.sleep(1)

    def _go_home(self):
        self._move(_HOME, 50, 1)

    def _pick_only(self, goal_handle):
        self.get_logger().info("Pick start")

        self._go_home()
        self._gripper_open()
        self._move(_PICK, 30, 1)
        self._gripper_close()
        self._go_home()

        self._send_status(goal_handle, 1)  # pick
        self.get_logger().info("Pick finished")

    # ==============================
    # 좌표 경로
    # ==============================
    positions = {
        (3, 1): [[6, 0, 0, 0, 0, 45], [6, 0, -40, 35, 0, 46]],
        (3, 2): [[-10, 0, 0, 0, 0, 45], [-10, -11, -40, 53, 0, 46]],
        (3, 3): [[-35, 0, 0, 0, 0, 45], [-35, -37.7, 8.4, 32.3, -1.8, 46]],
        (3, 4): [[-47, 0, 0, 0, 0, 45], [-47, -51.5, 20.3, 36.5, -1.4, 46]],
        (3, 5): [[-70, 0, 0, 0, 0, 45], [-70, -50.71, 20.3, 36.5, -2.8, 46]],
        (3, 6): [[-81, 0, 0, 0, 0, 45], [-74.1, -51.5, 13, 50.7, -12, 45]],

        (2, 1): [[6, 0, 0, 0, 0, 45], [6, 65.4, -134.8, 66.8, 3, 45], [6, 9.2, -109.3, 100, 0, 45]],
        (2, 2): [[-10, 0, 0, 0, 0, 45], [-10, 65.4, -134.8, 66.8, 0, 45], [-10, -1, -106.2, 109, 0, 45]],
        (2, 3): [[-35, 0, 0, 0, 0, 45], [-35, 65.4, -134.8, 56.8, 0, 45], [-35, -10.8, -94.3, 109, 0, 45]],
        (2, 4): [[-47, 0, 0, 0, 0, 45], [-47, 65.4, -134.8, 56.8, 0, 45], [-47, -18.1, -89.2, 112, -1, 45]],
        (2, 5): [[-70, 0, 0, 0, 0, 45], [-70, 65.4, -134.8, 56.8, 0, 45], [-70, -25.9, -81.9, 115, -2.8, 45]],
        (2, 6): [[-81, 0, 0, 0, 0, 45], [-81, 65.4, -134.8, 56.8, 10, 45], [-74, -21, -90, 115, -12, 45]],

        (1, 1): [[4, 0, 0, 0, 0, 45], [4, 61.5, -150, 93.2, 0, 45], [6, 61.5, -150, 70, 0, 45], [6, 8.3, -127.3, 93, 0, 45]],
        (1, 2): [[-10, 0, 0, 0, 0, 45], [-10, 61.5, -150, 93.2, 0, 45], [-10, 61.5, -150, 70, 0, 45], [-10, 2.5, -129.6, 103.6, 0, 45]],
        (1, 3): [[-35, 0, 0, 0, 0, 45], [-35, 61.5, -150, 93.2, 0, 45], [-35, 61.5, -150, 70, 0, 45], [-35, -13.4, -116.2, 110, 0, 45]],
        (1, 4): [[-47, 0, 0, 0, 0, 45], [-47, 61.5, -150, 93.2, 0, 45], [-47, 61.5, -150, 70, 0, 45], [-47, -28.7, -112.5, 127, 0, 45]],
        (1, 5): [[-70, 0, 0, 0, 0, 45], [-70, 61.5, -150, 93.2, 0, 45], [-68, 61.5, -150, 70, 0, 45], [-68, -21.4, -108.1, 111, -2.8, 45]],
        (1, 6): [[-81, 0, 0, 0, 0, 45], [-81, 61.5, -150, 93.2, 0, 45], [-81, 61.5, -150, 70, 0, 45], [-79.6, -42.4, -100.5, 135, -3.3, 45]],
    }

    # ==============================
    # 작업 함수
    # ==============================
    def _place_after_pick(self, i, j):
        if (i, j) not in self.positions:
            raise ValueError(f"잘못된 적재 좌표: {i}층 {j}칸")

        path = self.positions[(i, j)]
        self.get_logger().info(f"{i}층 {j}칸 적재 시작")

        # 이미 pick이 끝나서 물체를 잡고 있다고 가정
        self._go_home()

        for idx, angles in enumerate(path):
            self._move(angles, 50 if idx == 0 else 30, 2)

        self._gripper_open()

        for idx, angles in enumerate(reversed(path)):
            self._move(angles, 30 if idx == 0 else 50, 2)

        self._go_home()

    def _retrieve(self, i, j):
        if (i, j) not in self.positions:
            raise ValueError(f"잘못된 출고 좌표: {i}층 {j}칸")

        path = self.positions[(i, j)]
        self.get_logger().info(f"{i}층 {j}칸 출고 시작")

        self._go_home()
        self._gripper_open()

        for idx, angles in enumerate(path):
            self._move(angles, 50 if idx == 0 else 30, 2)

        self._gripper_close()

        for idx, angles in enumerate(reversed(path)):
            self._move(angles, 30 if idx == 0 else 50, 2)

        self._go_home()
        self._move(_PICK, 30, 2)
        self._gripper_open()
        self._go_home()

    def _defective_after_pick(self):
        self.get_logger().info("불량품 처리 시작")

        # 이미 pick이 끝나서 물체를 잡고 있다고 가정
        self._go_home()

        self._move([-110, 0, 0, 0, 0, 45], 50, 3)
        self._move([-110, -70, 0, 0, 0, 45], 30, 1)

        self._gripper_open()

        self._move([-110, 0, 0, 0, 0, 45], 50, 3)
        self._go_home()

    # ==============================
    # Feedback
    # ==============================
    def _send_status(self, goal_handle, code):
        if goal_handle is None:
            return

        # code 1 = pick
        # code 9 = finish
        feedback_msg = Fibonacci.Feedback()
        feedback_msg.sequence = [int(code)]
        goal_handle.publish_feedback(feedback_msg)

        if code == 1:
            self.get_logger().info("Feedback: pick")
        elif code == 9:
            self.get_logger().info("Feedback: finish")
        else:
            self.get_logger().info(f"Feedback code: {code}")

    # ==============================
    # Goal 해석
    # ==============================
    def parse_order(self, order):
        mode = order // 100
        i = (order // 10) % 10
        j = order % 10
        return mode, i, j

    # ==============================
    # Action 실행
    # ==============================
    def execute_callback(self, goal_handle):
        order = goal_handle.request.order
        mode, i, j = self.parse_order(order)

        self.get_logger().info(
            f"Goal received: order={order}, mode={mode}, i={i}, j={j}"
        )

        result = Fibonacci.Result()

        try:
            if order == 400:
                self._pick_only(goal_handle)
                goal_handle.succeed()
                result.sequence = [1, order]
                return result

            if mode == 1:
                self._place_after_pick(i, j)

            elif mode == 2:
                self._retrieve(i, j)

            elif mode == 3:
                self._defective_after_pick()

            else:
                raise ValueError(f"Unknown order: {order}")

            self._send_status(goal_handle, 9)  # finish

            goal_handle.succeed()
            result.sequence = [1, order]
            self.get_logger().info(f"Task succeeded: order={order}")
            return result

        except Exception as e:
            self.get_logger().error(f"Task failed: {e}")
            goal_handle.abort()
            result.sequence = [0, order]
            return result


def main(args=None):
    rclpy.init(args=args)

    node = ExecuteTaskServer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()