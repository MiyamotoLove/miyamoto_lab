import sys
import tty
import termios
import threading
from time import sleep
from gpiozero import Servo


# ============================================================
# ESC設定
# ============================================================

# GPIO12 → 左ESC
# GPIO13 → 右ESC
#
# gpiozeroのServo.value
#
# -1.0  = 最大後退
#  0.0  = ニュートラル
# +1.0  = 最大前進
#
# ※ これはモーターPWMのDuty比ではありません。
#    ESCへのスロットル指令です。

motor_left = Servo( #LAM
    12,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)

motor_right = Servo( #REM
    13,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)


# ============================================================
# 操作設定
# ============================================================

# 最大出力
#
# 0.0 ～ 1.0
#
# 0.3 → 弱め
# 0.5 → 中程度
# 0.8 → 強め
# 1.0 → 最大前進/最大後退指令
#
MAX_POWER = 0.6

# ソフトストップ時の1回あたりの減少量
STOP_STEP = 0.05

# ソフトストップの更新間隔
STOP_DELAY = 0.1

# 方向転換するときにニュートラルで待つ時間
NEUTRAL_DELAY = 0.5


# ============================================================
# 状態
# ============================================================

state = "STOPPED"

current_power = 0.0
target_power = 0.0

running_flag = True

# 複数スレッドから状態を変更するのでLockを使用
lock = threading.Lock()


# ============================================================
# ESCへ出力
# ============================================================

def set_motor(power):
    """
    左右のESCに同じ出力を送る。

    power:
        -1.0 ～ +1.0

        -1.0 = 最大後退
         0.0 = ニュートラル
        +1.0 = 最大前進
    """

    motor_left.value = power
    motor_right.value = power


# ============================================================
# モーター制御スレッド
# ============================================================

def motor_worker():

    global state
    global current_power
    global target_power

    previous_power = 0.0

    while running_flag:

        with lock:
            local_state = state
            local_target = target_power
            local_current = current_power

        # ----------------------------------------------------
        # RUNNING
        # ----------------------------------------------------
        if local_state == "RUNNING":

            # 前進 → 後退
            # または
            # 後退 → 前進
            #
            # いきなり逆転させない
            if (
                local_current > 0.0 and
                local_target < 0.0
            ) or (
                local_current < 0.0 and
                local_target > 0.0
            ):

                print(
                    "\n方向転換のためニュートラルにします..."
                )

                set_motor(0.0)

                with lock:
                    current_power = 0.0

                sleep(NEUTRAL_DELAY)

                # 待っている間に終了された場合
                if not running_flag:
                    break

            else:
                # 通常の走行
                with lock:
                    current_power = local_target

                set_motor(local_target)

            sleep(0.05)

        # ----------------------------------------------------
        # SOFT_STOP
        # ----------------------------------------------------
        elif local_state == "SOFT_STOP":

            if abs(local_current) > 0.0:

                if local_current > 0.0:
                    new_power = local_current - STOP_STEP

                    if new_power < 0.0:
                        new_power = 0.0

                else:
                    new_power = local_current + STOP_STEP

                    if new_power > 0.0:
                        new_power = 0.0

                with lock:
                    current_power = new_power

                set_motor(new_power)

                sleep(STOP_DELAY)

            else:
                # 完全にニュートラル
                set_motor(0.0)

                with lock:
                    current_power = 0.0
                    target_power = 0.0
                    state = "STOPPED"

                sleep(0.05)

        # ----------------------------------------------------
        # STOPPED
        # ----------------------------------------------------
        elif local_state == "STOPPED":

            set_motor(0.0)

            with lock:
                current_power = 0.0
                target_power = 0.0

            sleep(0.05)


# ============================================================
# キーボード入力
# ============================================================

def get_key():

    fd = sys.stdin.fileno()

    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)

    finally:
        termios.tcsetattr(
            fd,
            termios.TCSADRAIN,
            old_settings
        )

    return ch


# ============================================================
# メイン処理
# ============================================================

print("========================================")
print("      クローラ ESC 制御開始")
print("========================================")

print()
print("ESCをニュートラルに初期化しています...")
print("2秒間お待ちください。")
print()

# 最初は必ずニュートラル
set_motor(0.0)

sleep(2.0)

print("初期化完了")
print()
print("操作:")
print("  W : 前進")
print("  S : 後退")
print("  A : なだらかに停止")
print("  D : 即停止（ニュートラル）")
print("  Q : 終了")
print()
print(f"最大出力: {MAX_POWER}")
print()


# ============================================================
# 制御スレッド開始
# ============================================================

thread = threading.Thread(
    target=motor_worker
)

thread.start()


try:

    while True:

        key = get_key().lower()

        # ----------------------------------------------------
        # W : 前進
        # ----------------------------------------------------

        if key == "w":

            with lock:

                # 現在後退中なら、一旦ニュートラル
                if current_power < 0.0:
                    state = "SOFT_STOP"
                    target_power = 0.0

                    # 次のループで停止処理

                    print(
                        "\r[SOFT_STOP] 後退からニュートラルへ..."
                        "                    ",
                        end=""
                    )

                else:

                    target_power = MAX_POWER
                    state = "RUNNING"

                    print(
                        f"\r[RUNNING] 前進 "
                        f"(出力 {MAX_POWER:.2f})       ",
                        end=""
                    )


        # ----------------------------------------------------
        # S : 後退
        # ----------------------------------------------------

        elif key == "s":

            with lock:

                # 現在前進中なら、一旦ニュートラル
                if current_power > 0.0:

                    state = "SOFT_STOP"
                    target_power = 0.0

                    print(
                        "\r[SOFT_STOP] 前進からニュートラルへ..."
                        "                    ",
                        end=""
                    )

                else:

                    target_power = -MAX_POWER
                    state = "RUNNING"

                    print(
                        f"\r[RUNNING] 後退 "
                        f"(出力 {-MAX_POWER:.2f})       ",
                        end=""
                    )


        # ----------------------------------------------------
        # A : ソフトストップ
        # ----------------------------------------------------

        elif key == "a":

            with lock:
                target_power = 0.0
                state = "SOFT_STOP"

            print(
                "\r[SOFT_STOP] なだらかに停止中..."
                "                    ",
                end=""
            )


        # ----------------------------------------------------
        # D : 即停止
        # ----------------------------------------------------

        elif key == "d":

            with lock:
                target_power = 0.0
                current_power = 0.0
                state = "STOPPED"

            set_motor(0.0)

            print(
                "\r[STOPPED] ニュートラル..."
                "                    ",
                end=""
            )


        # ----------------------------------------------------
        # Q : 終了
        # ----------------------------------------------------

        elif key == "q":

            print(
                "\n終了処理を行っています..."
            )

            break


# ============================================================
# Ctrl+C
# ============================================================

except KeyboardInterrupt:

    print(
        "\n\nCtrl+Cが入力されました。"
    )


# ============================================================
# 終了処理
# ============================================================

finally:

    print("モーターをニュートラルにしています...")

    with lock:
        running_flag = False
        state = "STOPPED"
        current_power = 0.0
        target_power = 0.0

    # ESCにニュートラルを送信
    set_motor(0.0)

    # スレッド終了待ち
    thread.join()

    # 念のためもう一度ニュートラル
    set_motor(0.0)

    sleep(0.5)

    motor_left.close()
    motor_right.close()

    print("モーターを安全に停止しました。")
    print("プログラムを終了します。")