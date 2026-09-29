import sys
import tty
import termios
import threading
from time import sleep
from gpiozero import Servo
from gpiozero import Device
print(Device.pin_factory)
# ============================================================
# ESC設定
# ============================================================

motor = Servo(
    12,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)

motor2 = Servo(
    13,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)


# ============================================================
# 設定パラメータ
# ============================================================

duty1 = 0.1       # 最大出力
step = 0.05       # ソフトストップ時の減速量
delay = 0.1       # ソフトストップ更新間隔

MIN_PULSE_US = 1000
MAX_PULSE_US = 2000


# ============================================================
# グローバル変数
# ============================================================

state = "STOPPED"
running_flag = True

current_duty = 0.0
target_duty = 0.0


# ============================================================
# Servo.value → パルス幅[µs]に変換
# ============================================================

def value_to_pulse_us(value):

    # -1.0 ～ +1.0 を1000～2000µsに変換

    pulse_us = (
        MIN_PULSE_US
        + (value + 1.0) / 2.0
        * (MAX_PULSE_US - MIN_PULSE_US)
    )

    return pulse_us


# ============================================================
# PWMモニター
# ============================================================

def pwm_monitor():

    global running_flag
    global current_duty
    global target_duty
    global state

    while running_flag:

        pulse1 = value_to_pulse_us(current_duty)
        pulse2 = value_to_pulse_us(current_duty)

        print(
            f"\r"
            f"[MONITOR] "
            f"STATE={state:<10} "
            f"VALUE={current_duty:+.3f} "
            f"GPIO12={pulse1:.1f}us "
            f"GPIO13={pulse2:.1f}us "
            f"TARGET={target_duty:+.3f}    ",
            end="",
            flush=True
        )

        sleep(0.2)


# ============================================================
# モーター制御スレッド
# ============================================================

def motor_worker():

    global state
    global current_duty
    global target_duty

    while running_flag:

        # ----------------------------------------------------
        # 通常運転
        # ----------------------------------------------------

        if state == "RUNNING":
            if current_duty != target_duty:
                current_duty = target_duty

                motor.value = current_duty
                motor2.value = current_duty

            sleep(0.1)


        # ----------------------------------------------------
        # 信号停止
        # ----------------------------------------------------

        elif state == "NO_SIGNAL":

            # gpiozeroのServoをcloseするわけではなく、
            # 現在の信号を維持しないための状態として扱う

            motor.value = 0.0
            motor2.value = 0.0

            current_duty = 0.0

            sleep(0.1)


        # ----------------------------------------------------
        # ソフトストップ
        # ----------------------------------------------------

        elif state == "SOFT_STOP":

            # 前進から停止

            if current_duty > 0.0:

                current_duty -= step

                if current_duty <= 0.0:

                    current_duty = 0.0
                    state = "STOPPED"


            # 後退から停止

            elif current_duty < 0.0:

                current_duty += step

                if current_duty >= 0.0:

                    current_duty = 0.0
                    state = "STOPPED"


            else:

                state = "STOPPED"


            motor.value = current_duty
            motor2.value = current_duty

            sleep(delay)


        # ----------------------------------------------------
        # 停止
        # ----------------------------------------------------

        elif state == "STOPPED":
            if current_duty != 0:
                current_duty = 0
                motor.value = 0
                motor2.value = 0

            sleep(0.1)


# ============================================================
# キー入力
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

print("=== クローラ(ESC)制御開始 ===")

print(
    "ESCの初期化を行っています。"
    "ニュートラル信号を送信中（2秒お待ちください）..."
)


# ------------------------------------------------------------
# ESC初期化
# ------------------------------------------------------------

motor.value = 0.0
motor2.value = 0.0

sleep(2)


print()
print(
    "操作:"
    " W=前進"
    " S=後退"
    " A=なだらかに停止"
    " D=即停止"
    " Z=信号停止"
    " Q=終了"
)

print()


# ============================================================
# スレッド開始
# ============================================================

motor_thread = threading.Thread(
    target=motor_worker
)

monitor_thread = threading.Thread(
    target=pwm_monitor
)


motor_thread.start()
monitor_thread.start()


# ============================================================
# キーボード処理
# ============================================================

try:

    while True:

        key = get_key().lower()


        # ----------------------------------------------------
        # 前進
        # ----------------------------------------------------

        if key == 'w':

            target_duty = duty1
            state = "RUNNING"

            print(
                f"\n[RUNNING] "
                f"前進 "
                f"(出力 {target_duty:.3f})"
            )


        # ----------------------------------------------------
        # 後退
        # ----------------------------------------------------

        elif key == 's':

            target_duty = -duty1
            state = "RUNNING"

            print(
                f"\n[RUNNING] "
                f"後退 "
                f"(出力 {target_duty:.3f})"
            )


        # ----------------------------------------------------
        # ソフトストップ
        # ----------------------------------------------------

        elif key == 'a':

            state = "SOFT_STOP"

            print(
                "\n[SOFT_STOP] "
                "なだらかに停止中..."
            )


        # ----------------------------------------------------
        # 信号停止
        # ----------------------------------------------------

        elif key == 'z':

            state = "NO_SIGNAL"

            print(
                "\n[NO_SIGNAL] "
                "ニュートラル信号を送信"
            )


        # ----------------------------------------------------
        # 即停止
        # ----------------------------------------------------

        elif key == 'd':

            state = "STOPPED"

            print(
                "\n[STOPPED] "
                "即座に停止しました。"
            )


        # ----------------------------------------------------
        # 終了
        # ----------------------------------------------------

        elif key == 'q':

            print(
                "\n終了処理を行っています..."
            )

            break


except KeyboardInterrupt:

    print(
        "\nCtrl+Cが入力されました。"
    )


finally:

    running_flag = False

    motor_thread.join()
    monitor_thread.join()


    # 安全停止

    motor.value = 0.0
    motor2.value = 0.0

    sleep(0.5)


    motor.close()
    motor2.close()


    print(
        "\nモータを安全に停止し、"
        "プログラムを終了しました。"
    )