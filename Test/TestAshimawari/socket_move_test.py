from pathlib import Path
import socket
import json
import time
"9/1の答え"
# PWM設定
""""
Lam = PWM0
Rem = PWM1

"""
PWM_CHIP = Path("/sys/class/pwm/pwmchip0")
LAM_PWM_NUM = 0
REM_PWM_NUM = 1

HOST = "0.0.0.0"
PORT = 5000

def value_to_pulse(value):
    """
    -1.0 から 1.0 のジョイスティック入力を 1300 から 1700 μs にスケーリング
    範囲外の値が来ても max/min でクリップして安全を担保する
    """
    pulse = int(1500 + (value * 200))
    return max(1300, min(1700, pulse))

def pwm_write(chip_path, channel, option, value):
    try:
        (chip_path / f"pwm{channel}" / option).write_text(str(int(value)))
    except Exception as e:
        print(f"PWM Write Error ({option}): {e}")

def set_pulse_width(chip_path, channel, value_us):
    if value_us < 1000 or value_us > 2000:
        print(f"Error: pulse width {value_us} is out of bounds")
        return
    duty_ns = int(value_us * 1000)
    pwm_write(chip_path, channel, "duty_cycle", duty_ns)

def pwm_setup(chip_path, channel, hz, neutral_pulse):
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
        pwm_write(chip_path, 0, "enable", 0)
    if (chip_path / "pwm1").exists():
        pwm_write(chip_path, 1, "enable", 0)

def main():
    print("Initializing PWM...")
    pwm_setup(PWM_CHIP, LAM_PWM_NUM, 50, 1500)
    pwm_setup(PWM_CHIP, REM_PWM_NUM, 50, 1500)
    print("PWM started.")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    print(f"Waiting for connection on port {PORT}...")

    # 外側のループ：クライアントとの接続・再接続を管理
    while True:
        client, address = server.accept()
        print(f"Connected from: {address}")
        
        # 連続したJSONデータを安全に分離するため、ソケットを行単位のファイルとして扱う
        client_file = client.makefile('r', encoding='utf-8')

        try:
            # 内側のループ：データの受信とモータ制御
            while True:
                line = client_file.readline()
                if not line:
                    print("PCから切断されました。再接続を待機します。")
                    break  # 内側のループを抜け、外側の accept() に戻る

                stick_data = json.loads(line.strip())
                
                # 計算と安全機構（範囲制限）は value_to_pulse 内で処理済み
                current_duty_lam = value_to_pulse(stick_data["Lam"])
                current_duty_rem = value_to_pulse(stick_data["Rem"])

                set_pulse_width(PWM_CHIP, LAM_PWM_NUM, current_duty_lam)
                set_pulse_width(PWM_CHIP, REM_PWM_NUM, current_duty_rem)

        except json.JSONDecodeError as e:
            print(f"JSONパースエラーが発生しました: {e}")
        except Exception as e:
            print(f"通信エラーが発生しました: {e}")
        finally:
            client.close()
            # 通信が切れたら、機体が暴走しないよう必ずニュートラルに戻す
            print("モータ出力をニュートラルにリセットします。")
            set_pulse_width(PWM_CHIP, LAM_PWM_NUM, 1500)
            set_pulse_width(PWM_CHIP, REM_PWM_NUM, 1500)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCtrl+C が入力されたため終了します。")
    finally:
        pwm_stop(PWM_CHIP)
        print("PWM stopped.")