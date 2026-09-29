#実機テスト

from MySPC import MySPC, PWM_CHIP, LAM_PWM_NUM, REM_PWM_NUM
from raspi_socket import RaspiSocket
import signal
import sys

"""
コントローラでクローラロボットを動かす（親機 Raspi 側）
PC側（pc_move.py）から {"Lam": -1.0〜1.0, "Rem": -1.0〜1.0} を受け取り、左右のクローラに反映する

Lam = PWM0（左クローラ）
Rem = PWM1（右クローラ）

必要なファイル（同じフォルダに置く）: MySPC.py, raspi_socket.py
"""

HOST = "0.0.0.0"
PORT = 5000

HZ = 50
NEUTRAL_PULSE = 1500

COMMAND_TIMEOUT = 0.3  # [秒] これ以上コマンドが来なければ停止（ウォッチドッグ）
LINK_TIMEOUT = 2.0     # [秒] これ以上何も来なければ切断して再接続待ちに戻る

# MySPC.stickdata_to_pulseus は「スティックを前に倒す → 1500より短いパルス」の向き。
# 9/1の答え（socket_move_test.py）は逆（前 → 1500より長いパルス）なので、
# タイヤを浮かせた状態で試し、前に倒して後ろに進むクローラは True にする
LAM_REVERSE = False
REM_REVERSE = False


def stop_crawler(LamCTL, RemCtl):
    """両方のクローラを停止（ニュートラル）にする"""
    LamCTL.set_pulse_widthus(NEUTRAL_PULSE)
    RemCtl.set_pulse_widthus(NEUTRAL_PULSE)


def move_crawler(LamCTL, RemCtl, lam, rem):
    """スティックの値（-1.0〜1.0）をそのまま左右のクローラに反映する"""
    if LAM_REVERSE:
        lam = -lam
    if REM_REVERSE:
        rem = -rem

    # 範囲外やNaNの処理（クランプ）は stickdata_to_pulseus 内で済んでいる
    LamCTL.set_pulse_widthus(LamCTL.stickdata_to_pulseus(lam))
    RemCtl.set_pulse_widthus(RemCtl.stickdata_to_pulseus(rem))


def main(LamCTL, RemCtl, SV):
    print("Initializing PWM...")
    if not (LamCTL.pwm_setup() and RemCtl.pwm_setup()):
        print("PWMのセットアップに失敗したため終了します。")
        return
    print("PWM started.")

    SV.start()

    # 外側のループ：PCとの接続・再接続を管理
    while True:
        # 接続待ちの間は、機体が暴走しないよう必ず停止しておく
        stop_crawler(LamCTL, RemCtl)
        SV.accept()

        # 内側のループ：データの受信とモータ制御
        # read_LamRem は次のとき [0, 0]（停止）を返すので、そのまま反映すれば止まる
        #   ・COMMAND_TIMEOUT 秒コマンドが届かない ・不正なデータ ・切断
        # 切断されると SV.connected が False になり、外側の accept() に戻る
        while SV.connected:
            lam, rem = SV.read_LamRem()
            move_crawler(LamCTL, RemCtl, lam, rem)

        print("モータ出力をニュートラルにリセットしました。再接続を待機します。")


if __name__ == "__main__":
    # systemd などから停止された（SIGTERM）ときも、finally を通ってPWMを止める
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    LamCTL = MySPC(PWM_CHIP, LAM_PWM_NUM, HZ, NEUTRAL_PULSE)
    RemCtl = MySPC(PWM_CHIP, REM_PWM_NUM, HZ, NEUTRAL_PULSE)
    SV = RaspiSocket(HOST, PORT, timeout=COMMAND_TIMEOUT, link_timeout=LINK_TIMEOUT)

    try:
        main(LamCTL, RemCtl, SV)
    except KeyboardInterrupt:
        print("\nCtrl+C が入力されたため終了します。")
    finally:
        # pwm_stop は、ニュートラルを出してから出力を止める
        RemCtl.pwm_stop()
        LamCTL.pwm_stop()
        SV.close()
        print("PWM stopped.")