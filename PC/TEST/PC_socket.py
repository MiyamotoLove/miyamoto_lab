import json
import socket

PI_IP = "100.109.70.44"
PORT = 5000

class PCSocket:

    """
        data = {
        "Rem": controller0.right_y,
        "Lam": controller0.left_y
        }

        How to use
          connect
          send_json(anytimes)

    """
    def __init__(self , rspi_ip= PI_IP , port = PORT):
        self.rspi_ip = rspi_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.connect((self.rspi_ip , self.port))

    def send_json(self , data):
        message = json.dumps(data) + "\n"
        self.sock.sendall(message.encode("utf-8"))

    def close(self):
        self.sock.close()


if __name__ == "__main__":
    TestPCSocket = PCSocket()
    TestPCSocket.connect()
    data = {
                "Rem": 1500,
                "Lam": 1500
            }

    TestPCSocket.send_json(data) 
    TestPCSocket.close()

