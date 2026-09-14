from pathlib import Path
from time import sleep
"""

動きました

pwm0,1は事前にexportしておいてください = code追加しよう
設計思想
pulseの時間はμs
周期はhz

set_pulse
setup
stop
のみを使用してください

"""
# PWM設定
PWM_CHIP = Path("/sys/class/pwm/pwmchip0")
current_duty_rem = 1500#dutyじゃなくて幅ですね
current_duty_lam = 1500

def pwm_write(chip_path, channel , option, value): #非推奨
    
    (chip_path/ f"pwm{channel}" / option).write_text(str(int(value)))


def set_pulse_width(chip_path, channel , value_us):#μ秒
    """
    PWMのパルス幅を設定する。
    
    pulse_us:
        パルス幅 [us]----------------------------------μs
    """
    if value_us < 1000 or value_us > 2000:
        print("Error: pulse width must be 1000-2000 us")
        return

    duty_ns = value_us * 1000

    pwm_write(chip_path , channel , "duty_cycle", duty_ns)

    print(f"Pulse width: {value_us} us")

def pwm_setup(chip_path , channel , hz , neutral_pulse):
    """
    
        chip_path
        channel
        hz
        netural_pulse μs
    
    """
    period_ns = int((1/ hz) *  1_000_000_000)

    # 周期
    pwm_write(chip_path , channel ,"period", period_ns)

    # 初期化,neutralを出すよ
    set_pulse_width(chip_path , channel, neutral_pulse)
    # PWM開始
    pwm_write(chip_path , channel , "enable", 1)



def pwm_stop(chip_path):
    """PWMを停止する。"""

    if (chip_path/"pwm0").exists():
        pwm_write(chip_path , 0 , "enable", 0)
    if (chip_path/"pwm1").exists():
        pwm_write(chip_path , 1 , "enable", 0)


def main():
    pwm_setup(PWM_CHIP , 0 , 50 , 1500)
    pwm_setup(PWM_CHIP , 1 , 50 , 1500)

    print("PWM started.")
    print("1: 1700 us")
    print("2: 1500 us")
    print("3: 1300 us")
    print("4: なだらかに1700へ加速")
    print("5:なだらかに1500へ減速")
    print("q: quit")

    while True:
        command = input("> ")

        if command == "1":

            current_duty_rem = 1700
            current_duty_lam = 1700
            set_pulse_width(PWM_CHIP , 0 , current_duty_lam)
            set_pulse_width(PWM_CHIP , 1 , current_duty_rem)

        elif command == "2":
            current_duty_rem = 1500
            current_duty_lam = 1500
            set_pulse_width(PWM_CHIP , 0 , current_duty_lam)
            set_pulse_width(PWM_CHIP , 1 , current_duty_rem)

        elif command == "3":
            current_duty_rem = 1300
            current_duty_lam = 1300
            set_pulse_width(PWM_CHIP , 0 , current_duty_lam)
            set_pulse_width(PWM_CHIP , 1 , current_duty_rem)

        elif command == "4":  # なだらか加速

            current_duty_rem = current_duty_lam

            while current_duty_lam < 1700:

                # 1500→1700の進行度 0.0～1.0
                progress = (current_duty_lam - 1500) / 200

                # 序盤は小さく、後半ほど大きくする
                step = int(5 + progress * 20)

                current_duty_lam += step

                if current_duty_lam > 1700:
                    current_duty_lam = 1700

                current_duty_rem = current_duty_lam

                set_pulse_width(PWM_CHIP, 0, current_duty_lam)
                set_pulse_width(PWM_CHIP, 1, current_duty_rem)

                sleep(0.1)


        elif command == "5":  # なだらか減速

            current_duty_rem = current_duty_lam

            while current_duty_lam > 1500:

                # 1700→1500の進行度 0.0～1.0
                progress = (1700 - current_duty_lam) / 200

                # 序盤は小さく、後半ほど大きくする
                step = int(5 + progress * 20)

                current_duty_lam -= step

                if current_duty_lam < 1500:
                    current_duty_lam = 1500

                current_duty_rem = current_duty_lam

                set_pulse_width(PWM_CHIP, 0, current_duty_lam)
                set_pulse_width(PWM_CHIP, 1, current_duty_rem)

                sleep(0.1)




        elif command == "q":
            break

        else:
            print("Invalid command.")


try:
    main()

except KeyboardInterrupt:

    print(
        "\nCtrl+Cが入力されました。"
    )

finally:
    pwm_stop(PWM_CHIP)
    print("PWM stopped.")