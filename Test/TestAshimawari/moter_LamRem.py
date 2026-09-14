from pathlib import Path
import time
import os


PWM_CHIP = Path("/sys/class/pwm/pwmchip0")
LAM_PWM_NUM = 0
REM_PWM_NUM = 1



#----------------------------------------------------------------------
#Pwm0 , 1 maker

def setting_pwmchip(pwm_channel):
    pwm_dir = f"/sys/class/pwm/pwmchip0/pwm{pwm_channel}"
    
    if not os.path.exists(pwm_dir):
        "pwm{pwm_channel}を作成 (export) "
        try:
            with open("/sys/class/pwm/pwmchip0/export", "w") as f:
                f.write(str(pwm_channel))

            time.sleep(0.1)
        except PermissionError:
            print("エラー: 権限がありません。sudo で実行してください。")
            return False
    else:
        "pwm{pwm_channel} はすでに作成されています。"

    
    try:
        #period（周期）設定
        # 例：20000000ナノ秒 = 20ミリ秒 = 50Hz
        with open(f"{pwm_dir}/period", "w") as f:
            f.write("20000000")
            
        with open(f"{pwm_dir}/enable", "w") as f:
            f.write("1")
            
        return True
        
    except Exception as e:
        print(f"pwm{pwm_channel} の設定中にエラー: {e}")
        return False



#----------------------------------------------------------------------


def value_to_pulse(value):
    """
    -1.0 から 1.0 のジョイスティック入力を 1300 から 1700 μs にスケーリング
    範囲外の値が来ても max/min でクリップして安全を担保する
    """
    pulse = int(1500 + (value * 200))
    return max(1300, min(1700, pulse))

def pwm_write(chip_path, channel, option, value):#使用非推奨。
    try:
        (chip_path / f"pwm{channel}" / option).write_text(str(int(value)))
    except Exception as e:
        print(f"PWM Write Error ({option}): {e}")

def set_pulse_width(chip_path, channel, value_us): #使っていいよ
    if value_us < 1000 or value_us > 2000:
        print(f"Error: pulse width {value_us} is out of bounds")
        pwm_write(chip_path, channel, "duty_cycle", 1500 * 1000)
        return None

    duty_ns = int(value_us * 1000)
    pwm_write(chip_path, channel, "duty_cycle", duty_ns)

def pwm_setup(chip_path, channel, hz, neutral_pulse):

    setting_pwmchip(channel)

    pwm_dir = chip_path / f"pwm{channel}"
    
    # 1. PWMの有効化（export）
    if not pwm_dir.exists():
        try:
            (chip_path / "export").write_text(str(channel))
            time.sleep(0.1)  # OSがファイルを生成するのを待つ
        except Exception as e:
            print(f"Error: PWM channel {channel} export failed. ({e})")
            return

    # 2. 周期とニュートラルの設定
    period_ns = int((1 / hz) * 1_000_000_000)
    pwm_write(chip_path, channel, "period", period_ns)
    set_pulse_width(chip_path, channel, neutral_pulse)
    pwm_write(chip_path, channel, "enable", 1)

def pwm_stop(chip_path):
    """プログラム終了時にPWMを安全に停止する"""
    if (chip_path / "pwm0").exists():
        set_pulse_width(chip_path, 0 , 1500)
        pwm_write(chip_path, 0, "enable", 0)
    if (chip_path / "pwm1").exists():
        set_pulse_width(chip_path, 1 , 1500)
        pwm_write(chip_path, 1, "enable", 0)
        

def main():
    pwm_setup(PWM_CHIP, LAM_PWM_NUM, 50, 1500)
    pwm_setup(PWM_CHIP, REM_PWM_NUM, 50, 1500)

    # 外側のループ：クライアントとの接続・再接続を管理
    while True:

        # 連続したJSONデータを安全に分離するため、ソケットを行単位のファイルとして扱う

        try:
            # 内側のループ：データの受信とモータ制御
            while True:

                
                # 計算と安全機構（範囲制限）は value_to_pulse 内で処理済み
                current_duty_lam = value_to_pulse(stick_data["Lam"])
                current_duty_rem = value_to_pulse(stick_data["Rem"])

                set_pulse_width(PWM_CHIP, LAM_PWM_NUM, current_duty_lam)
                set_pulse_width(PWM_CHIP, REM_PWM_NUM, current_duty_rem)

        finally:

            pwm_stop(PWM_CHIP)