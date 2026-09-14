from gpiozero import Servo
from time import sleep

esc = Servo(
    12,
    min_pulse_width=0.001,
    max_pulse_width=0.002
)

print("GPIO13 ニュートラル探索")
print("モーターから手を離してください")
print()

# -0.10 ～ +0.10 を0.01刻みで試す
for value in [x / 100 for x in range(-10, 11)]:
    value += 0.2
    print(f"Servo.value = {value:+.2f}")

    esc.value = value

    sleep(2)

print("最後にニュートラル")
esc.value = 0

sleep(3)

esc.close()