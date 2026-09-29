from gpiozero import PhaseEnableMotor
from time import sleep

# 物理ピン11(GPIO17)をDIRに、物理ピン32(GPIO12)をPWMに指定
motor = PhaseEnableMotor(phase=17, enable=12)

try:
    print("モータ始動")
    # 0.0 から 1.0 の間で徐々に加速させる
    # for i in range(6):
    #     speed = i / 10.0
    #     motor.forward(speed)
    #     print("duty比:", speed)
    #     sleep(0.5)
    
    
    # sleep(5)

    # for i in range(5):
    #     speed = (5-i) / 10.0
    #     motor.forward(speed)
    #     print("duty比:", speed)
    #     sleep(0.5)

    # sleep(3)
    # motor.stop()

except KeyboardInterrupt:
    pass
finally:
    motor.stop()