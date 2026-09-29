from pc_socket import PCSocket
from PC_controller import Controller
import pygame
import time

"""
コントローラでクローラロボットを動かす（PC側）
左スティックの上下 → 左クローラ（Lam）
右スティックの上下 → 右クローラ（Rem）

必要なファイル（同じフォルダに置く）: pc_socket.py, PC_controller.py
先に親機（Raspi）側で socket_move.py を起動しておくこと
（先にこちらを起動しても、つながるまで自動で再接続し続ける）
"""

RASPI_HOST = "100.109.70.44"  # ← 親機ラズパイのIPアドレスに変更すること
RASPI_PORT = 5000

CONTROLLER_NUM = 0
SEND_HZ = 50              # [Hz] 送信周期。値が変わらなくても毎回送る（親機のウォッチドッグ用）
RECONNECT_INTERVAL = 1.0  # [秒] 再接続を試みる間隔

STOP_DATA = {"Lam": 0.0, "Rem": 0.0}

# 安全装置：起動時・コントローラ再接続時は、スティックが中央に
# NEUTRAL_HOLD 秒続くまで停止しか送らない（軸番号の設定ミスなどで勝手に走り出すのを防ぐ）
NEUTRAL_THRESHOLD = 0.2   # これ未満なら「スティックが中央にある」とみなす
NEUTRAL_HOLD = 0.5        # [秒]
WARN_INTERVAL = 2.0       # [秒] 中央にならないときの警告を出す間隔


def is_neutral(data):
    return abs(data["Lam"]) < NEUTRAL_THRESHOLD and abs(data["Rem"]) < NEUTRAL_THRESHOLD


def connect():
    """親機に接続する。できたら PCSocket、できなければ None を返す"""
    try:
        pc = PCSocket(RASPI_HOST, RASPI_PORT)
        print(f"Connected to {RASPI_HOST}:{RASPI_PORT}")
        return pc
    except OSError as e:
        print(f"接続できません（{e}）。{RECONNECT_INTERVAL}秒後に再試行します。")
        return None


def main(controller0):
    clock = pygame.time.Clock()
    pc = None
    last_try = time.monotonic() - RECONNECT_INTERVAL

    armed = False          # True になるまでは停止しか送らない
    neutral_since = None
    last_warn = time.monotonic() - WARN_INTERVAL

    try:
        while True:
            # 送りすぎると親機側に処理待ちが溜まるので、周期を固定する
            clock.tick(SEND_HZ)

            # コントローラが抜けている間は、read() で全部0（停止）になる
            controller0.read()
            data = {
                "Lam": controller0.left_y,
                "Rem": controller0.right_y
            }

            # コントローラが抜けたら、挿し直した後にもう一度中立確認をやり直す
            if not controller0.connected:
                armed = False
                neutral_since = None

            if not armed:
                now = time.monotonic()
                if controller0.connected and is_neutral(data):
                    if neutral_since is None:
                        neutral_since = now
                    if now - neutral_since >= NEUTRAL_HOLD:
                        armed = True
                        print("スティックの中立を確認しました。操縦できます。")
                else:
                    neutral_since = None
                    if controller0.connected and now - last_warn >= WARN_INTERVAL:
                        print(f"スティックが中央にありません（Lam={data['Lam']:+.2f}, Rem={data['Rem']:+.2f}）。"
                              "手を離しても直らない場合は PC_controller.py の AXIS_MAP を確認してください。")
                        last_warn = now
                data = STOP_DATA

            # 未接続なら、一定間隔で接続を試みる
            if pc is None:
                if time.monotonic() - last_try < RECONNECT_INTERVAL:
                    continue
                last_try = time.monotonic()
                pc = connect()
                if pc is None:
                    continue

            try:
                pc.send_json(data)
            except OSError as e:
                # 途中まで送れている可能性があるので、この接続は捨てて作り直す
                print(f"送信エラー（{e}）。再接続します。")
                pc.close_socket()
                pc = None

    finally:
        if pc is not None:
            try:
                pc.send_json(STOP_DATA)  # 最後に停止を伝えてから閉じる
            except OSError:
                pass
            pc.close_socket()


if __name__ == "__main__":
    controller0 = Controller(CONTROLLER_NUM)

    try:
        main(controller0)
    except KeyboardInterrupt:
        print("\nCtrl+C が入力されたため終了します。")
    finally:
        controller0.exit()
        pygame.quit()