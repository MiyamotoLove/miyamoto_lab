import socket
import json


class PCSocket:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send_json(self, data):
        message = json.dumps(data) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def receive_json(self):
        """
        JSONを受信してPythonのdictなどに戻す
        """
        data = self.sock.recv(1024)

        if not data:
            raise ConnectionError("接続が切断されました")

        message = data.decode("utf-8").strip()
        return json.loads(message)

    def close_socket(self):#これだけでいいのかは定かじゃない
        """
        ソケットを閉じる
        """
        self.sock.close()

    