import pygame
"""
data = {
    "Rem": controller0.right_y,
    "Lam": controller0.left_y
}

readは_axisで二桁に丸めてるから、問題あったら教えて

軸番号はOS・ドライバ・コントローラの機種で変わるので、
本番のPCで python PC_controller.py を実行して確認し、AXIS_MAP を合わせること
（例：Linux + Xbox系 → 右スティックは 3, 4 / Windows + Xbox系 → 2, 3 になることが多い）

実機確認：スティックを前に倒すと 1（左）と 3（右）が -1 になる
→ Windows + Xbox系の配置。4, 5 はトリガー（触らないと -1）なので絶対に使わないこと
"""

AXIS_MAP = {"left_x": 0, "left_y": 1, "right_x": 2, "right_y": 3}
DEADZONE = 0.1


def apply_deadzone(value, deadzone):
    """
    |value| < deadzone なら 0
    それ以外はデッドゾーンの外側を 0〜1 に引き伸ばして、微速域も使えるようにする
    """
    if abs(value) < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * min(1.0, (abs(value) - deadzone) / (1.0 - deadzone))


class Controller:

    def __init__(self, number, axis_map=None, deadzone=DEADZONE):#number一つ目が0

        pygame.init()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        if number >= count:
            raise RuntimeError(f"コントローラ {number} 番が見つかりません（接続数: {count}）")

        self.axis_map = dict(AXIS_MAP if axis_map is None else axis_map)
        self.deadzone = deadzone

        self.joystick = pygame.joystick.Joystick(number)
        self.joystick.init()
        self.instance_id = self.joystick.get_instance_id()
        self.connected = True

        needed = max(self.axis_map.values()) + 1#axis_mapによる必要は軸の数
        if self.joystick.get_numaxes() < needed:#get_numaxes()はコントローラの軸の数を返す
            raise RuntimeError(f"軸が {self.joystick.get_numaxes()} 本しかありません（{needed} 本必要）")

        self.left_x = 0
        self.left_y = 0
        self.right_x = 0
        self.right_y = 0

    def _axis(self, name, invert=False):#いきるん外部から呼び出さんといてこの関数
        value = apply_deadzone(self.joystick.get_axis(self.axis_map[name]), self.deadzone)
        if invert:
            value = -value
        return round(value, 2) + 0.0  # + 0.0 で -0.0 を 0.0 にそろえれるらしい=>学びになるなぁ

    def read(self):#y軸前が正にしてるよ
        # 抜き差しのイベントを見る（pygame.event.pump() の代わり）
        for event in pygame.event.get():
            if (event.type == pygame.JOYDEVICEREMOVED
                    and self.connected and event.instance_id == self.instance_id):
                print("コントローラが切断されました。")
                self.connected = False
            elif event.type == pygame.JOYDEVICEADDED and not self.connected:
                try:
                    self.joystick = pygame.joystick.Joystick(event.device_index)
                    self.joystick.init()
                    self.instance_id = self.joystick.get_instance_id()
                    self.connected = True
                    print("コントローラが再接続されました。")
                except pygame.error as e:
                    print(f"コントローラを開けませんでした: {e}")

        # 抜けている間は全部0（停止）にする
        if not self.connected:
            self.left_x = 0
            self.left_y = 0
            self.right_x = 0
            self.right_y = 0
            return

        self.left_x = self._axis("left_x")
        self.left_y = self._axis("left_y", invert=True)#ここ機能してるか不安。
        self.right_x = self._axis("right_x")
        self.right_y = self._axis("right_y", invert=True)

    def exit(self):
        if self.connected:
            self.joystick.quit()
        self.connected = False


if __name__ == "__main__":#軸番号の確認用（Ctrl+Cで終了）
    pygame.init()
    js = pygame.joystick.Joystick(0)
    print(f"{js.get_name()} / 軸の数: {js.get_numaxes()}")
    clock = pygame.time.Clock()
    try:
        while True:
            pygame.event.pump()#これでstickが更新される
            print("  ".join(f"{i}:{js.get_axis(i):+.2f}" for i in range(js.get_numaxes())), end="\r")
            clock.tick(10)
    except KeyboardInterrupt:
        print()
    finally:
        pygame.quit()