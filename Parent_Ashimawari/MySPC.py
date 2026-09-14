from pathlib import Path
import time
import os

"実機"
"予定"
PWM_CHIP = Path("/sys/class/pwm/pwmchip0")
LAM_PWM_NUM = 0
REM_PWM_NUM = 1

class MySPC:
    def __init__(self , chip_path , pwm_channel , hz , neutral_pulse):
        self.chip_path = chip_path
        self.pwm_channel = pwm_channel
        self.pwm_dir = self.chip_path / f"pwm{self.pwm_channel}"
        self.hz = hz
        self.neutral_pulse = neutral_pulse
        print("必ずsetupしてから使用してください。")

    def pwm_setup(self):
        
        if not os.path.exists(self.pwm_dir):
            "pwm{pwm_channel}をexport "
            try:
                with open("/sys/class/pwm/pwmchip0/export", "w") as f:
                    f.write(str(self.pwm_channel))

                time.sleep(0.1)
            except PermissionError:
                print("エラー: 権限がありません。sudo で実行してください。")
                return False
            except Exception as e:
                print(f"Error: PWM channel {self.pwm_channel} export failed. ({e})")
                return False
    
        try:
            #period（周期）設定
            # 例：20000000ナノ秒 = 20ミリ秒 = 50Hz
            with open(f"{self.pwm_dir}/period", "w") as f:
                f.write(str(int(1/self.hz * 1_000_000_000)))
                
            with open(f"{self.pwm_dir}/enable", "w") as f:
                f.write("1")

            self.set_pulse_widthus(self.neutral_pulse)
                
            return True
            
        except Exception as e:
            print(f"pwm{self.pwm_channel} の設定中にエラー: {e}")
            return False



    def pwm_write(self , option , value):
        try:
            (self.pwm_dir / str(option)).write_text(str(int(value)))
        except Exception as e:
            print(f"PWM 書き込みエラー : {e}" )

    def stickdata_to_pulseus(self , value):
        """
        -1.0 から 1.0 のジョイスティック入力を 1700 から 1300 μs にスケーリング
        範囲外の値が来ても max/min でクリップして安全を担保する
        """
        pulse = int(1500 + ( - value * 200))
        return max(1300, min(1700, pulse))#ここ俺頭いい番兵

    def set_pulse_widthus(self , value_us):

        value_us = int(value_us)

        if value_us < 1000 or value_us > 2000:
            print(f"pulseの入力値が不正 {value_us}")
            self.pwm_write("duty_cycle" , 1500 * 1000)
            return None

        duty_ns = value_us * 1000
        self.pwm_write("duty_cycle" , duty_ns)

    def pwm_stop(self):

        if(self.pwm_dir).exists():
            self.set_pulse_widthus(1500)
            self.pwm_write("enable" ,0)
        else:
            print("Oh my god! Start shitenainoni Stop!?")


if __name__ == '__main__':#使用例

    try : 
        LamCTL = MySPC(PWM_CHIP ,LAM_PWM_NUM , 50 , 1500)
        RemCtl = MySPC(PWM_CHIP , REM_PWM_NUM , 50 , 1500)

        LamCTL.pwm_setup()
        RemCtl.pwm_setup()

        print("SetUp完了")
        time.sleep(2)
        LamCTL.set_pulse_widthus(1600)
        RemCtl.set_pulse_widthus(1400)
        time.sleep(2)

    except KeyboardInterrupt:
        print("\nCtrl+C が入力されたため終了します。")
    finally:
        RemCtl.pwm_stop()
        LamCTL.pwm_stop()
        print("PWM stopped.")
    
        
