from gpiozero import Servo
from time import sleep
import sys
import tty
import termios


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
# パルス幅設定
# ============================================================

pulse_us = 1500


# ============================================================
# パルス幅 → Servo.value
# ============================================================

def pulse_to_value(pulse_us):
    return (pulse_us - 1500) / 500


# ============================================================
# ESCへパルスを出力
# ============================================================

def set_pulse(pulse_us):

    value = pulse_to_value(pulse_us)

    motor.value = value
    motor2.value = value

    print(
        f"\rPulse = {pulse_us} us"
        f"    Servo.value = {value:+.4f}",
        end="",
        flush=True
    )


# ============================================================
# キーを1文字取得
# ============================================================

def get_key():

    fd = sys.stdin.fileno()

    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        key = sys.stdin.read(1)

    finally:
        termios.tcsetattr(
            fd,
            termios.TCSADRAIN,
            old_settings
        )

    return key


# ============================================================
# 初期化
# ============================================================

print("========================================")
print("       ESC ニュートラル探索")
print("========================================")

print()
print("1500 us を出力します。")
print("ESCを初期化しています...")
print()

set_pulse(1500)

sleep(3)

print()
print()
print("操作:")
print("  W : +1 us")
print("  S : -1 us")
print("  Q : 終了")
print()
print("現在: 1500 us")


# ============================================================
# メインループ
# ============================================================

try:

    while True:

        key = get_key().lower()

        # ----------------------------------------------------
        # +1 us
        # ----------------------------------------------------

        if key == "w":

            pulse_us += 1

            if pulse_us > 2000:
                pulse_us = 2000

            set_pulse(pulse_us)


        # ----------------------------------------------------
        # -1 us
        # ----------------------------------------------------

        elif key == "s":

            pulse_us -= 1

            if pulse_us < 1000:
                pulse_us = 1000

            set_pulse(pulse_us)


        # ----------------------------------------------------
        # 終了
        # ----------------------------------------------------

        elif key == "q":

            break


finally:

    print()
    print()
    print("1500 us に戻します。")

    set_pulse(1500)

    sleep(1)

    motor.close()
    motor2.close()

    print("終了しました。")