import socket
import json
import math
import select
import time
from collections import deque

""""
実機予定
read_LamRemはPWMの値じゃないことに留意してください。
Lam = PWM0
Rem = PWM1

"""

MAX_BUFFER_BYTES = 64 * 1024  # 改行が来ないままこれを超えたら異常とみなす


class RaspiSocket:

    """"この順番で実行なさい
    start(void)
    accept(void) -- connection成功まで停止
    read_LamRem(void)ーー繰り返しな
    close(Void)

    read_LamRem は次のとき [0 , 0]（停止）を返す
      ・timeout 秒以内にコマンドが届かなかった（ウォッチドッグ）
      ・切断された / 不正なデータだった
    切断されたかは self.connected で確認して、False なら accept() し直すこと

    """

    def __init__(self , host = "0.0.0.0" , port = 5000 , timeout = 0.3 , link_timeout = 2.0):#0.0.0.0は有線LANでもwlan0でもいいよてきなあれ
        self.host = host
        self.port = int(port)
        self.timeout = timeout            # これ以上コマンドが来なければ [0, 0] を返す
        self.link_timeout = link_timeout  # これ以上何も来なければ接続が死んだとみなして切る
        self.server = None
        self.client = None
        self.address = None
        self.connected = False
        self._buf = b""
        self._lines = deque()
        self._last_rx = 0.0
        self._halted = False

    def start(self):

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        print(f"Waiting for connection on port {self.port}...")

    def accept(self):
        self._close_client()  # 前の接続が残っていれば閉じてから待つ
        self.client, self.address = self.server.accept()
        print(f"Connected from: {self.address}")
        self._buf = b""
        self._lines.clear()
        self._last_rx = time.monotonic()
        self._halted = False
        self.connected = True

    def _read_lines(self , timeout):
        """
        timeout秒まで待って、届いた「改行で終わる行」をまとめて返す（来なければ空リスト）
        1行でも取れたら、それ以上は待たずに今読める分だけ読み切る
        TCPはバイトの流れなので、1回のrecvが1メッセージとは限らない
        → バッファに溜めて改行ごとに切り出し、途中までの行は次回に持ち越す
        timeout=None なら1行届くまで待ち続ける
        """
        if not self.connected:
            return []

        deadline = None if timeout is None else time.monotonic() + timeout
        lines = []

        while True:
            if lines:
                wait = 0.0
            elif deadline is None:
                wait = None
            else:
                wait = max(0.0, deadline - time.monotonic())

            readable, _, _ = select.select([self.client], [], [], wait)
            if not readable:
                return lines

            try:
                chunk = self.client.recv(4096)
            except OSError as e:
                print(f"読み込みエラー: {e}")
                self._close_client()
                return lines

            if not chunk:
                print("PCから切断されました。再接続を待機します。")
                self._close_client()
                return lines

            self._last_rx = time.monotonic()
            self._buf += chunk
            *new_lines, self._buf = self._buf.split(b"\n")
            lines.extend(line.decode("utf-8", errors="replace") for line in new_lines)

            if len(self._buf) > MAX_BUFFER_BYTES:
                print("改行のないデータが大量に来たため切断します。")
                self._close_client()
                return lines

            # 変なデータが流れ続けても、timeoutを超えて居座らない
            if deadline is not None and time.monotonic() >= deadline:
                return lines

    def read(self):
        """1行を文字列で返す（読めなければ0）"""
        if not self._lines:
            self._lines.extend(self._read_lines(None))

        if not self._lines:
            print("読み込めませんでした。")
            return 0
        return self._lines.popleft() + "\n"

    def read_LamRem(self):

        lines = list(self._lines)
        self._lines.clear()
        lines += self._read_lines(self.timeout)

        # 溜まっていた古いコマンドは捨てて「最新」だけを使う（遅延が積み上がらないように）
        latest = None
        for line in lines:
            stick_data = self._parse(line)
            if stick_data is not None:
                latest = stick_data

        if latest is not None:
            if self._halted:
                print("受信が再開しました。")
                self._halted = False
            return latest

        # ここに来たら、新しい正しいコマンドが無い → 停止
        if self.connected:
            if not self._halted:
                print(f"{self.timeout}秒以上コマンドが届かないため停止します。")
                self._halted = True
            if time.monotonic() - self._last_rx >= self.link_timeout:
                print("通信途絶が続いたため切断します。再接続を待機します。")
                self._close_client()

        return [0 , 0]

    @staticmethod
    def _to_stick_value(value):
        # boolはintの一種なので明示的に弾く
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"数値ではありません: {value!r}")
        value = float(value)
        # json.loads は NaN や Infinity も受け付けてしまうので弾く
        if not math.isfinite(value):
            raise ValueError(f"有限の数ではありません: {value!r}")
        return max(-1.0, min(1.0, value))

    def _parse(self , line):
        """1行をパースして [Lam , Rem] を返す（不正なら None）"""

        stick_data = line.strip()
        if not stick_data:
            return None

        try:
            stick_data = json.loads(stick_data)
        except json.JSONDecodeError:
            print("受信データが不正なJSONでした。")
            return None

        if not isinstance(stick_data, dict):
            print("思いもよらぬデータが来ました。")
            return None

        try:
            stick_data_Lam = self._to_stick_value(stick_data["Lam"])
            stick_data_Rem = self._to_stick_value(stick_data["Rem"])
        except KeyError as e:
            print(f"思いもよらぬデータが来ました。（キー {e} がありません）")
            return None
        except (TypeError, ValueError) as e:
            print(f"思いもよらぬデータが来ました。（{e}）")
            return None

        return [stick_data_Lam , stick_data_Rem]

    def _close_client(self):
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # すでに切れている場合など
            self.client.close()
            print("クライアントとの接続を閉じました。")
        self.client = None
        self.address = None
        self.connected = False
        self._buf = b""
        self._lines.clear()

    def close(self):

        self._close_client()

        if self.server is not None:
            self.server.close()
            self.server = None
            print("サーバーを停止しました。")

if __name__ == "__main__":
    SV = RaspiSocket("0.0.0.0", 5000)

    try:
        SV.start()
        print("まってるなう")
        SV.accept()
        for i in range(10):
            print(10 - i)


            time.sleep(1)


        print(SV.read_LamRem())
    finally:
        SV.close()
