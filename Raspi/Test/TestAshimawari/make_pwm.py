import os
import time
#Change
def setup_pwm(pwm_channel):
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

# 実行
print("--- PWMの初期化を開始 ---")
setup_pwm(0)  # Lam用 (PWM0)
setup_pwm(1)  # Rem用 (PWM1)
print("こんにちは")