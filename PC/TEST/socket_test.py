import socket
import json

PI_IP = "192.168.10.11"
PORT = 5000

def send_json(sock , data):
    message = json.dumps(data) + "\n"
    sock.sendall(message.encode("utf-8"))

def receive_json(sock):
    """
    JSONを受信してPythonのdictなどに戻す
    """
    data = sock.recv(1024)

    if not data:
        raise ConnectionError("接続が切断されました")

    message = data.decode("utf-8").strip()
    return json.loads(message)


def send_number(sock, value):
    """
    数値を送信する
    """
    message = f"{value}\n"
    sock.sendall(message.encode("utf-8"))


def receive_number(sock):
    """
    数値を受信して float に変換する
    """
    data = sock.recv(1024)

    if not data:
        raise ConnectionError("接続が切断されました")

    value = float(data.decode("utf-8").strip())
    return value


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((PI_IP, PORT))

    print("Connected to Raspberry Pi")

    data = {
        "left": 1500,
        "right": 1600
    }

    send_json(sock, data)

    


    sock.close()


main()