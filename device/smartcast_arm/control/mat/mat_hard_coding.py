import time

# ==============================
# 공통 함수
# ==============================
def move_angles(mc, angles, speed=50, delay=3):
    mc.send_angles(angles, speed)
    time.sleep(delay)

def move_z(mc, delta_z, speed=30, delay=2):
    coords = mc.get_coords()
    target = coords.copy()
    target[2] += delta_z
    mc.send_coords(target, speed, 0)
    time.sleep(delay)

def grip_open(mc, speed=100, delay=1):
    mc.set_gripper_value(100, speed)
    time.sleep(delay)

def grip_close(mc, speed=100, delay=1):
    mc.set_gripper_value(0, speed)
    time.sleep(delay)


# ==============================
# 패턴 1
# ==============================
def pattern_1(mc):
    move_angles(mc, [0,0,0,0,0,45], 50, 1)
    grip_open(mc)

    move_angles(mc, [90,0,0,0,0,45])
    move_angles(mc, [90,17.5,-144.8,38,0,45]) # 4 

    grip_close(mc) # 5 
    move_z(mc, +50) # 6

    move_angles(mc, [90,0,0,0,0,45]) # 7
    move_angles(mc, [0,0,0,0,0,45])

    move_angles(mc, [0,0,0,-17.31,0,-45])
    move_angles(mc, [0,-76.6,0,-17.31,0,-45], 100)

    move_angles(mc, [0,0,0,0,0,-45], 50, 1)
    move_angles(mc, [90,0,0,0,0,45])

    move_angles(mc, [90,25.2,-111.5,-7,0,45])
    move_z(mc, -60)

    grip_open(mc)

    move_angles(mc, [90,25.2,-111.5,-7,0,45])
    move_angles(mc, [0,0,0,0,0,45])


# ==============================
# 패턴 2
# ==============================
def pattern_2(mc):
    move_angles(mc, [0,0,0,0,0,45], 50, 1)
    grip_open(mc)

    move_angles(mc, [90,0,0,0,0,45])
    move_angles(mc, [90,-16,-114,42,0,45])

    grip_close(mc)
    move_z(mc, +50)

    move_angles(mc, [90,0,0,0,0,45])
    move_angles(mc, [0,0,0,0,0,45])

    move_angles(mc, [0,0,0,-17.31,0,-45])
    move_angles(mc, [0,-76.6,0,-17.31,0,-45], 100)

    move_angles(mc, [0,0,0,0,0,-45], 50, 1)
    move_angles(mc, [90,0,0,0,0,45])

    move_angles(mc, [90,-10,-63,-17,0,45])
    move_z(mc, -70)

    grip_open(mc)

    move_angles(mc, [90,-11.2,-63.3,-22.5,0,45])
    move_angles(mc, [0,0,0,0,0,45])


# ==============================
# 패턴 3
# ==============================
def pattern_3(mc):
    move_angles(mc, [0,0,0,0,0,45], 50, 1)
    grip_open(mc)

    move_angles(mc, [90,0,0,-90,0,45])
    move_angles(mc, [90,-43,-69,23,0,45])

    grip_close(mc)
    move_z(mc, +50)

    move_angles(mc, [0,0,0,0,0,45])

    move_angles(mc, [0,0,0,-17.31,0,-45])
    move_angles(mc, [0,-76.6,0,-17.31,0,-45], 100)

    move_angles(mc, [0,0,0,0,0,-45], 50, 1)
    move_angles(mc, [90,0,0,0,0,45])

    move_angles(mc, [90,0,0,-90,0,45])
    move_angles(mc, [90,-36.12,-63.28,9.05,0,45])

    move_z(mc, -10)
    grip_open(mc)
    move_z(mc, +60)

    move_angles(mc, [0,0,0,0,0,45])


# ==============================
# 실행부
# ==============================
choice = input("패턴 선택 (1 / 2 / 3): ")

if choice == "1":
    pattern_1(mc)
elif choice == "2":
    pattern_2(mc)
elif choice == "3":
    pattern_3(mc)
else:
    print("잘못된 입력")


# ==============================
# Pouring
# ==============================
move_angles(mc, [0,0,0,0,0,45], 50, 1)
grip_open(mc)

move_angles(mc, [-90,0,0,0,0,45])
move_angles(mc, [-90,-86,0,90,0,45])

grip_close(mc)

move_angles(mc, [-90,0,0,0,0,45])
move_angles(mc, [0,0,0,0,0,45], 50, 1)

move_angles(mc, [0,0,-142,143,1,45])
move_angles(mc, [0,0,-142,143,1,125], 10, 10)
move_angles(mc, [0,0,-142,143,1,45], 50, 1)

move_angles(mc, [0,0,0,0,0,45], 50, 1)

move_angles(mc, [-90,0,0,0,0,45])
move_angles(mc, [-90,-87,0,90,0,45])

grip_open(mc)

move_angles(mc, [-90,0,0,0,0,45])
move_angles(mc, [0,0,0,0,0,45], 50, 1)


# ==============================
# Demolding
# ==============================
move_angles(mc, [0,0,0,0,0,45])
grip_open(mc)

move_angles(mc, [0,0,0,-17.31,0,45])
move_angles(mc, [0,-76.6,0,-17.31,0,45], 100)

move_z(mc, -10)
grip_close(mc)

move_angles(mc, [0,0,0,0,0,45], 50, 1)
move_angles(mc, [-30.9,-60.3,0,24,0,45])

grip_open(mc)

move_angles(mc, [0,0,0,0,0,45])