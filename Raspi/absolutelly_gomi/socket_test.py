import socket
import json

HOST = "0.0.0.0"
PORT = 5000


def send_number(sock, value):
    """
    数値を送信する
    """
    message = f"{value}\n"
    sock.sendall(message.encode("utf-8"))

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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen(1)

    print("Waiting for connection...")

    client, address = server.accept()
    print("Connected:", address)

    data = receive_json(client)
    print(data)
    print(data["left"])
    print(data["right"])

    client.close()
    server.close()

main()