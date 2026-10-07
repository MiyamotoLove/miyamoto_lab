import socket
import json
"""
With as PCSocket(...) as sock:を使った方がBetter
"""
class PCSocket:

    def __init__(self, host, port, timeout=1.0):
        self.host = host
        self.port = port
        self._buf = b""#バイト型
        # 接続先がいないときに永久に固まらないよう、タイムアウト付きで接続
        # （このタイムアウトは以降の送受信にも効く）
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        # 小さいパケットを溜めずに即送る（操縦の遅延対策）
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send_json(self, data):
        """
        dictなどをJSONにして1行で送る（末尾に改行）
        失敗したら OSError（タイムアウト含む）が出る。
        途中まで送れている可能性があるので、その接続は閉じて作り直すこと
        """
        # Not a Number / Infinity は JSON の規格外なので、送る前に弾く
        message = json.dumps(data, allow_nan=False) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def receive_json(self):
        """
        JSONを受信してPythonのdictなどに戻す
        TCPはバイトの流れなので、改行が来るまでバッファに溜めてから1行ずつ切り出す
        """
        while b"\n" not in self._buf:
            if len(self._buf) > 64 * 1024:
                raise ConnectionError("受信データが長すぎます（区切りの改行がありません）")

            data = self.sock.recv(4096)

            if not data:
                raise ConnectionError("接続が切断されました")

            self._buf += data

        line, self._buf = self._buf.split(b"\n", 1)#splitは1度だけ分割,lineは改行まで
        return json.loads(line.decode("utf-8"))#辞書型にする

    def close_socket(self):
        """
        ソケットを閉じる
        """
        try:
            self.sock.shutdown(socket.SHUT_RDWR)  # 相手に「もう送らない」を伝える
        except OSError:
            pass  # すでに切れている場合など
        self.sock.close()

    # with PCSocket(...) as sockとは、 
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close_socket()
        return False
