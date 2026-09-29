from pathlib import Path

from time import sleep

"""
動きました。
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
current_duty_rem = 1500#dutuじゃなくて幅ですね
current_duty_lam = 1500



def pwm_write(chip_path, channel , option, value): #非推奨
    (chip_path/ f"pwm{channel}" / option).write_text(str(value))


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
    print("q: quit")

    while True:
        command = input(">")

        if command == "1":
            current_duty_rem = 1700
            current_duty_lam = 1700

        elif command == "2":
            current_duty_rem = 1500
            current_duty_lam = 1500

        elif command == "3":
            current_duty_rem = 1300
            current_duty_lam = 1300

        elif command == "4":#なだらかstart

            
            
            if current_duty_lam <= 1700:
                current_duty_lam += (1700- current_duty_lam) * 0.5
                if current_duty_lam > 1700:
                    current_duty_lam = 1700

            if current_duty_rem <= 1700:
                current_duty_rem += (1700 - current_duty_rem) * 0.5
                if current_duty_rem > 1700:
                    current_duty_rem = 1700

        elif command == "5" : #なだらかstop

            if current_duty_lam >= 1300:
                current_duty_lam -= (current_duty_lam - 1300) * 0.5
                if current_duty_lam < 1300:
                    current_duty_lam = 1300

            if current_duty_rem >= 1300:
                current_duty_rem -= (current_duty_rem - 1300)* 0.5
                if current_duty_rem < 1300:
                    current_duty_rem = 1300

            

        elif command == "q":
            break

        else:
            print("Invalid command.")

        set_pulse_width(PWM_CHIP , 0 , current_duty_rem)
        set_pulse_width(PWM_CHIP , 1 , current_duty_lam)



try:
    main()

except KeyboardInterrupt:

    print(
        "\nCtrl+Cが入力されました。"
    )

finally:
    pwm_stop(PWM_CHIP)
    print("PWM stopped.")