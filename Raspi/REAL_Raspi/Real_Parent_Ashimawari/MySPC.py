from pathlib import Path
import math
import time
import os

"""

  実機
  予定
  親機（Raspi）のクローラー制御用

"""

PWM_CHIP = Path("/sys/class/pwm/pwmchip0")
LAM_PWM_NUM = 0
REM_PWM_NUM = 1

class MySPC:
    def __init__(self , chip_path , pwm_channel , hz , neutral_pulse , span_us = 200):
        self.chip_path = Path(chip_path)
        self.pwm_channel = pwm_channel
        self.pwm_dir = self.chip_path / f"pwm{self.pwm_channel}"
        self.hz = hz
        self.neutral_pulse = neutral_pulse
        self.span_us = span_us  # スティック±1.0のとき中立から何μs動かすか（200 → 1300〜1700μs）
        self.period_ns = int(1 / self.hz * 1_000_000_000)
        self.is_setup = False
        print("必ずsetupしてから使用してください。")

    def _wait_writable(self , timeout = 1.0):
        # export直後は、ファイルの生成や権限の設定が終わるまで少し時間がかかる
        period = self.pwm_dir / "period"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if period.exists() and os.access(period, os.W_OK):
                return True
            time.sleep(0.05)
        return False

    def pwm_setup(self):

        if not self.pwm_dir.exists():
            # pwm{pwm_channel}をexport
            try:
                (self.chip_path / "export").write_text(str(self.pwm_channel))
            except PermissionError:
                print("エラー: 権限がありません。sudo で実行してください。")
                return False
            except Exception as e:
                print(f"Error: PWM channel {self.pwm_channel} export failed. ({e})")
                return False

            if not self._wait_writable():
                print(f"Error: pwm{self.pwm_channel} をexportしましたが、書き込めるようになりませんでした。")
                return False

        # 前回の設定が残っていると「duty_cycle > 新しいperiod」で弾かれるので、先に0にする
        # 例：20000000ナノ秒 = 20ミリ秒 = 50Hz
        # enableより先に中立パルスを設定して、有効化した瞬間から中立を出す
        ok = (self.pwm_write("duty_cycle" , 0)
              and self.pwm_write("period" , self.period_ns)
              and self.pwm_write("duty_cycle" , self.neutral_pulse * 1000)
              and self.pwm_write("enable" , 1))

        if not ok:
            print(f"pwm{self.pwm_channel} の設定に失敗しました。")
            return False

        self.is_setup = True
        return True

    def pwm_write(self , option , value):
        """書き込めたらTrue、失敗したらFalseを返す"""
        try:
            (self.pwm_dir / str(option)).write_text(str(int(value)))
            return True
        except Exception as e:
            print(f"PWM 書き込みエラー（pwm{self.pwm_channel}/{option}）: {e}" )
            return False

    def stickdata_to_pulseus(self , value):
        """
        -1.0 から 1.0 のジョイスティック入力を 1700 から 1300 μs にスケーリング
        数値でない値やNaNが来たら中立、範囲外の値は端にクランプして安全を担保する
        """
        try:
            value = float(value)
        except (TypeError, ValueError):
            return self.neutral_pulse
        if not math.isfinite(value):
            return self.neutral_pulse

        value = max(-1.0, min(1.0, value))  # クランプ（範囲外を±1.0に収める）
        return round(self.neutral_pulse + (- value * self.span_us))

    def set_pulse_widthus(self , value_us):
        """書き込めたらTrue、失敗したらFalseを返す"""

        if not self.is_setup:
            print(f"pwm{self.pwm_channel} はsetupされていません。")
            return False

        try:
            value_us = int(value_us)
        except (TypeError, ValueError, OverflowError):
            value_us = -1

        if value_us < 1000 or value_us > 2000:
            print(f"pulseの入力値が不正 {value_us}")
            value_us = self.neutral_pulse

        duty_ns = value_us * 1000
        return self.pwm_write("duty_cycle" , duty_ns)

    def pwm_stop(self):

        if(self.pwm_dir).exists():
            self.pwm_write("duty_cycle" , self.neutral_pulse * 1000)
            time.sleep(3 / self.hz)  # ドライバに中立パルスを数回届けてから止める
            self.pwm_write("enable" , 0)
        else:
            print("Oh my god! Start shitenainoni Stop!?")

        self.is_setup = False


if __name__ == '__main__':#使用例

    LamCTL = MySPC(PWM_CHIP ,LAM_PWM_NUM , 50 , 1500)
    RemCtl = MySPC(PWM_CHIP , REM_PWM_NUM , 50 , 1500)

    try :
        if not (LamCTL.pwm_setup() and RemCtl.pwm_setup()):
            raise SystemExit("SetUpに失敗したため終了します。")

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
