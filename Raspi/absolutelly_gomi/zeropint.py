from gpiozero import Servo
from time import sleep


# ============================================================
# 設定
# ============================================================

GPIO_PIN = 12

START_VALUE = 0.1998
END_VALUE   = 0.2002

# 0.0001刻み
STEP = 0.0001

# 各値を出力する時間
WAIT_TIME = 2.0


# ============================================================
# ESC
# ============================================================

esc = Servo(
    GPIO_PIN,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)


print("======================================")
print(" GPIO13 ニュートラル詳細探索")
print("======================================")
print()
print(f"{START_VALUE:.4f} ～ {END_VALUE:.4f}")
print(f"{STEP:.4f} 刻みで探索します")
print()
print("判定:")
print("  F = 正転")
print("  R = 逆転")
print("  S = 停止")
print()
print("モーターを安全な状態にしてください。")
sleep(2)


# ============================================================
# 探索
# ============================================================

value = START_VALUE

forward_values = []
reverse_values = []
stopped_values = []

while value <= END_VALUE + 0.00001:

    value = round(value, 4)

    print()
    print("--------------------------------------")
    print(f"Servo.value = {value:.4f}")
    print("--------------------------------------")

    esc.value = value

    sleep(WAIT_TIME)

    answer = input(
        "F=正転 / R=逆転 / S=停止 : "
    ).strip().upper()

    if answer == "F":
        forward_values.append(value)

    elif answer == "R":
        reverse_values.append(value)

    elif answer == "S":
        stopped_values.append(value)

    else:
        print("無効な入力です。")

    value += STEP


# ============================================================
# 結果
# ============================================================

print()
print("======================================")
print(" 探索結果")
print("======================================")

if forward_values:
    print(
        f"正転範囲: "
        f"{min(forward_values):.4f} ～ "
        f"{max(forward_values):.4f}"
    )

if stopped_values:
    print(
        f"停止範囲: "
        f"{min(stopped_values):.4f} ～ "
        f"{max(stopped_values):.4f}"
    )

if reverse_values:
    print(
        f"逆転範囲: "
        f"{min(reverse_values):.4f} ～ "
        f"{max(reverse_values):.4f}"
    )


# ============================================================
# 正転→逆転の境界
# ============================================================

if forward_values and reverse_values:

    last_forward = max(forward_values)
    first_reverse = min(reverse_values)

    center = (
        last_forward + first_reverse
    ) / 2

    print()
    print("======================================")
    print(" ニュートラル候補")
    print("======================================")

    print(
        f"最後の正転 : {last_forward:.4f}"
    )

    print(
        f"最初の逆転 : {first_reverse:.4f}"
    )

    print(
        f"境界の中心 : {center:.4f}"
    )

    print()
    print(
        "推奨ニュートラル値:"
    )

    print(
        f"esc.value = {center:.4f}"
    )

else:

    print()
    print(
        "正転と逆転の両方を確認できませんでした。"
    )


# ============================================================
# 最後はニュートラル側に戻す
# ============================================================

if forward_values and reverse_values:

    esc.value = center

else:

    esc.value = 0.19

sleep(3)

esc.close()

print()
print("ESCを停止状態にして終了しました。")