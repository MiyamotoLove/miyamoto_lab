import socket
import json
import time

""""
実機予定
read_LamRemはPWMの値じゃないことに留意してください。
Lam = PWM0
Rem = PWM1

"""


class RaspiSocket:

    """"この順番で実行なさい
    start(void)
    accept(void) -- connection成功まで停止
    readLemRam(void)ーー繰り返しな
    close(Void)
    
    """

    def __init__(self , host = "0.0.0.0" , port = 5000):#0.0.0.0は優先LANでもwlan0でもいいよてきなあれ
        self.host = host
        self.port = int(port)

    def start(self):
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        print(f"Waiting for connection on port {self.port}...")

    def accept(self):
        self.client, self.address = self.server.accept()
        print(f"Connected from: {self.address}")
        self.client_file = self.client.makefile('r', encoding='utf-8')

    def read(self):
        try:
            line = self.client_file.readline()
            if not line:
                print("読み込めませんでした。")
                return 0
            return line
        except Exception as e:
            print(f"読み込みエラー: {e}")
            return 0

    def read_LamRem(self):

        try:
            line = self.client_file.readline()

            if not line:
                print("PCから切断されました。再接続を待機します。")
                return [0 , 0]

            # stick_data = json.loads(line.strip())
            stick_data = line.strip()

            if not stick_data:
                print("思いもよらぬデータが来ました。")
                return [0 , 0]

            stick_data = json.loads(stick_data)

            # 計算と安全機構（範囲制限）は value_to_pulse 内で処理済み
            stick_data_Lam = stick_data["Lam"]
            stick_data_Rem = stick_data["Rem"]

            return [stick_data_Lam , stick_data_Rem]

        except json.JSONDecodeError:
            print("受信データが不正なJSONでした。")
            return [0, 0]
        except Exception as e:
            print(f"予期せぬエラー: {e}")
            return [0, 0]

    def close(self):

        if hasattr(self, 'client_file'):
            self.client_file.close()
        if hasattr(self, 'client'):
            self.client.close()

        print("クライアントとの接続を閉じました。")

        if hasattr(self, 'server'):
            self.server.close()
            print("サーバーを停止しました。")

if __name__ == "__main__":
    SV = RaspiSocket("0.0.0.0", 5000)

    SV.start()
    print("まってるなう")
    SV.accept()
    for i in range(10):
        print(10 - i)


        time.sleep(1)


    print(SV.read_LamRem())
    SV.close()