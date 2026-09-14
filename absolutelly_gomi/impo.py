import sys
import tty
import termios
import threading
from time import sleep
from gpiozero import PWMOutputDevice

# 物理ピン32(GPIO12)をPWM出力として指定（DIRピンの設定は削除）
motor = PWMOutputDevice(12)

# --- 設定パラメータ ---
duty1 = 0.8  # Aを押したときのDuty比（0.0〜1.0）
step = 0.05  # Sを押したときの減速ステップ
delay = 0.1  # 減速の更新間隔（秒）

# --- グローバル変数 ---
state = "STOPPED"  # 現在の状態 (RUNNING, SOFT_STOP, STOPPED)
running_flag = True # 私が編集したよNANOで
current_duty = 0.0

def motor_worker():
    """モータの制御を独立して行うスレッド"""
    global state, current_duty
    
    while running_flag:
        if state == "RUNNING":
            current_duty = duty1
            # PWMOutputDeviceでは .value プロパティに0.0〜1.0を代入してDuty比を制御します
            motor.value = current_duty
            sleep(0.1)
            
        elif state == "SOFT_STOP":
            # なだらかに停止するループ
            while current_duty > 0.0 and state == "SOFT_STOP":
                current_duty -= step
                if current_duty <= 0.0:
                    current_duty = 0.0
                    state = "STOPPED"
                    motor.value = 0.0
                    break
                motor.value = current_duty
                sleep(delay)
                
        elif state == "STOPPED":
            motor.value = 0.0
            current_duty = 0.0
            sleep(0.1)

def get_key():
    """Enterキー不要で1文字入力を受け付ける関数"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# --- メイン処理 ---
print("=== 単一PWMモータ制御開始 ===")
print("操作: 'A'=回転, 'S'=なだらかに停止, 'D'=即停止, 'Q'=終了")

# モータ制御スレッドの起動
thread = threading.Thread(target=motor_worker)
thread.start()

try:
    while True:
        # キー入力を待機
        key = get_key().lower()
        
        if key == 'a':
            state = "RUNNING"
            print("\r[RUNNING] Duty {:.1f} で回転中...       ".format(duty1), end="")
        
        elif key == 's':
            state = "SOFT_STOP"
            print("\r[SOFT_STOP] なだらかに停止中...          ", end="")
            
        elif key == 'd':
            state = "STOPPED"
            print("\r[STOPPED] 即座に停止しました。           ", end="")
            
        elif key == 'q':
            print("\r終了処理を行っています...                ")
            break
            
except KeyboardInterrupt:
    print("\nCtrl+Cが入力されました。")
finally:
    # プログラム終了時の安全処理
    running_flag = False
    thread.join()
    motor.value = 0.0  # モータ出力を確実に0にする
    motor.close()      # リソースの解放
    print("\nモータを安全に停止し、プログラムを終了しました。")
