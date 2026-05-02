import time

# ─── Fixed joint angles ───────────────────────────────────────────────────────

_HOME          = [90, 0, 0, 0, 0, 45]
_AMR_HANDOFF   = [90, -20.39, -36.56, -7.99, 0, 45]
_DEFECT_HOVER  = [-110, 0, 0, 0, 0, 45]
_DEFECT_DROP   = [-110, -70, 0, 0, 0, 45]

# ─── Slot paths: (row, col) → [waypoint, ...] ────────────────────────────────

_SLOT_PATHS = {
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

# ─── Primitives ───────────────────────────────────────────────────────────────

def _move(angles, speed=30, delay=1):
    mc.send_angles(angles, speed)
    time.sleep(delay)

def _gripper_open():
    mc.set_gripper_value(100, 50)
    time.sleep(1)

def _gripper_close():
    mc.set_gripper_value(0, 50)
    time.sleep(1)

def _go_home():
    _move(_HOME, 50)

def _amr_handoff_pick():
    """AMR에서 물건 집어서 HOME으로 복귀."""
    _move(_AMR_HANDOFF, 30)
    _gripper_close()
    _go_home()

def _amr_handoff_drop():
    """AMR 위에 물건 내려놓고 HOME으로 복귀."""
    _move(_AMR_HANDOFF, 30, 2)
    _gripper_open()
    _go_home()

def _defect_drop():
    """불량품 투하 후 HOME으로 복귀."""
    _move(_DEFECT_HOVER, 50, 3)
    _move(_DEFECT_DROP, 30)
    _gripper_open()
    _move(_DEFECT_HOVER, 50, 3)
    _go_home()

# ─── Operations ───────────────────────────────────────────────────────────────

def PA_GP(row, col):
    if (row, col) not in _SLOT_PATHS:
        print("잘못된 좌표")
        return
    path = _SLOT_PATHS[(row, col)]
    print(f"{row}층 {col}칸 적재 시작")

    _go_home()
    _gripper_open()
    _amr_handoff_pick()

    for idx, angles in enumerate(path):
        _move(angles, 50 if idx == 0 else 30, 2)
    _gripper_open()
    for idx, angles in enumerate(reversed(path)):
        _move(angles, 30 if idx == 0 else 50, 2)

    _go_home()


def PICK(row, col):
    if (row, col) not in _SLOT_PATHS:
        print("잘못된 좌표")
        return
    path = _SLOT_PATHS[(row, col)]
    print(f"{row}층 {col}칸 출고 시작")

    _go_home()
    _gripper_open()

    for idx, angles in enumerate(path):
        _move(angles, 50 if idx == 0 else 30, 2)
    _gripper_close()
    for idx, angles in enumerate(reversed(path)):
        _move(angles, 30 if idx == 0 else 50, 2)

    _amr_handoff_drop()


def PA_DP():
    print("불량품 처리 시작")

    _go_home()
    _gripper_open()
    _amr_handoff_pick()
    _defect_drop()


# ─── Entry point ──────────────────────────────────────────────────────────────

mode = input("모드 선택 (1: PA_GP 적재, 2: PICK 출고, 3: PA_DP 불량품): ")
if mode == "3":
    PA_DP()
else:
    row = int(input("층 입력 (1~3): "))
    col = int(input("칸 입력 (1~6): "))

    if mode == "1":
        PA_GP(row, col)
    elif mode == "2":
        PICK(row, col)
    else:
        print("잘못된 입력")
