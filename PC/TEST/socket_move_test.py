import pygame
import json
import socket
import time
#なんか正転逆転になっている
PI_IP = "100.109.70.44"
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

class Controller:

    def __init__(self, number):
        self.joystick = pygame.joystick.Joystick(number)
        self.joystick.init()

        self.left_x = 0
        self.left_y = 0
        self.right_x = 0
        self.right_y = 0

    def read(self):
        pygame.event.pump()

        self.left_x = round(self.joystick.get_axis(0), 1)
        self.left_y = - round(self.joystick.get_axis(1) , 1)
        self.right_x = round(self.joystick.get_axis(2) , 1)
        self.right_y =  -round(self.joystick.get_axis(3) ,1 )

    def exit(self):
        self.joystick.quit()
    

def main():
    pygame.init()
    pygame.joystick.init()

    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.connect((PI_IP, PORT))

        print("Connected to Raspberry Pi")
        
        controller0 = Controller(0)
        
        while True:

            controller0.read()

            print(
                f"\r"
                f"左: Y={controller0.left_y}"
                f"右: Y={controller0.right_y}",
                end=""
            )


            data = {
                "Rem": controller0.right_y,
                "Lam": controller0.left_y
            }

            send_json(sock, data)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n終了")

    finally:
        controller0.exit()
        pygame.quit()

main()