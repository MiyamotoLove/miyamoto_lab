#!/usr/bin/env python3
"""
pca9685_motor.py

Raspberry Pi + AE-PCA9685（秋月電子）で、モータドライバを PWM 制御（デューティ比変更）する。

■ 想定している配線（PCA9685 の ch0〜ch2 の 3 本を使用）
    PCA9685 ch0 → モータドライバ PWM（速度 = デューティ比）
    PCA9685 ch1 → モータドライバ IN1（回転方向）
    PCA9685 ch2 → モータドライバ IN2（回転方向）
    PCA9685 GND → モータドライバ GND（GND は必ず共通にする）

  TB6612FNG（PWMA / AIN1 / AIN2）や L298N（ENA / IN1 / IN2）のような
  「PWM 1 本 + 方向 2 本」タイプのドライバを想定しています。
  割り当てが違う場合は、下の CH_PWM / CH_IN1 / CH_IN2 を書き換えてください。

■ ラズパイとの接続
    ラズパイ 3.3V(1番ピン) → PCA9685 VDD
    ラズパイ SDA (3番ピン) → PCA9685 SDA
    ラズパイ SCL (5番ピン) → PCA9685 SCL
    ラズパイ GND (6番ピン) → PCA9685 GND
    PCA9685 OE             → GND（またはオープン。High だと全出力が止まる）

■ 準備
    1. I2C を有効化:   sudo raspi-config → Interface Options → I2C → Yes
    2. ライブラリ:     sudo apt install python3-smbus2
                       （入らない場合は python3-smbus でも動きます）
    3. 接続確認:       i2cdetect -y 1
                       → 40 と 70 が表示されれば OK
                         （40 が本体のアドレス、70 は全デバイス一斉呼び出し用のアドレス）

■ 使い方
    python3 pca9685_motor.py           # 対話モード（デューティ比を数値で入力）
    python3 pca9685_motor.py --demo    # 加速 → 減速 → 逆転 のテスト動作
    python3 pca9685_motor.py --addr 0x41 --freq 1000   # アドレス・周波数を変更

  ※ 最初はタイヤを浮かせた状態で動作確認してください。
"""

import argparse
import signal
import sys
import time

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus  # python3-smbus（使うメソッドは smbus2 と同じ）


# ============================================================
#  設定（環境に合わせて変更する）
# ============================================================
I2C_BUS = 1            # ラズパイの I2C バス番号（GPIO2/3 は 1 番）
PCA9685_ADDR = 0x40    # アドレスジャンパを触っていなければ 0x40
PWM_FREQ_HZ = 1500     # PWM 周波数。PCA9685 の上限は約 1526Hz

CH_PWM = 0             # 速度（デューティ比）を出すチャンネル
CH_IN1 = 1             # 方向 IN1
CH_IN2 = 2             # 方向 IN2

INVERT = False         # 正転と逆転が逆なら True にする
MAX_DUTY = 1.0         # デューティ比の上限（0.0〜1.0）。最初は 0.5 などに絞ると安全


# ============================================================
#  PCA9685 本体（レジスタを直接操作する）
# ============================================================
class PCA9685:
    # レジスタアドレス
    MODE1 = 0x00
    MODE2 = 0x01
    LED0_ON_L = 0x06      # ch n のレジスタは LED0_ON_L + 4*n から 4 バイト
    ALL_LED_ON_H = 0xFB
    ALL_LED_OFF_H = 0xFD
    PRE_SCALE = 0xFE

    # MODE1 のビット
    RESTART = 0x80
    AI = 0x20             # レジスタ番号の自動インクリメント（4 バイト一括書き込みに必要）
    SLEEP = 0x10
    ALLCALL = 0x01

    # MODE2 のビット
    OUTDRV = 0x04         # 出力をトーテムポールにする（モータドライバの入力を直接駆動できる）

    OSC_HZ = 25_000_000   # 内部発振器の周波数（公称値。個体差で数 % ずれる）
    FULL = 0x10           # ON_H / OFF_H の bit4。立てるとそれぞれ「完全ON」「完全OFF」

    def __init__(self, bus, address=0x40):
        self.bus = bus
        self.address = address
        self.freq_hz = None

    def _write(self, reg, value):
        self.bus.write_byte_data(self.address, reg, value & 0xFF)

    def _read(self, reg):
        return self.bus.read_byte_data(self.address, reg)

    def setup(self, freq_hz):
        """初期化。全チャンネルを OFF にしてから PWM を開始する。"""
        # スリープ状態のまま設定する（起動途中に変な出力が出ないように）
        self._write(self.MODE1, self.AI | self.ALLCALL | self.SLEEP)
        self._write(self.MODE2, self.OUTDRV)
        self.all_off()
        return self.set_frequency(freq_hz)

    def set_frequency(self, freq_hz):
        """PWM 周波数を設定する（全チャンネル共通）。実際の周波数を返す。"""
        prescale = round(self.OSC_HZ / (4096 * freq_hz)) - 1
        prescale = max(3, min(255, prescale))  # 有効範囲は 3〜255（約 1526Hz〜24Hz）

        mode = self._read(self.MODE1) & ~(self.RESTART | self.SLEEP) & 0xFF
        self._write(self.MODE1, mode | self.SLEEP)  # PRE_SCALE はスリープ中しか書き込めない
        self._write(self.PRE_SCALE, prescale)
        self._write(self.MODE1, mode)               # スリープ解除
        time.sleep(0.005)                           # 発振器の安定待ち（データシート上は 500μs）
        self._write(self.MODE1, mode | self.RESTART)

        self.freq_hz = self.OSC_HZ / (4096 * (prescale + 1))
        return self.freq_hz

    def set_duty(self, channel, duty):
        """channel のデューティ比を設定する。duty: 0.0〜1.0"""
        if not 0 <= channel <= 15:
            raise ValueError(f"チャンネル番号が範囲外です: {channel}")

        if duty <= 0.0:
            on, off = 0, self.FULL << 8          # 完全OFF
        elif duty >= 1.0:
            on, off = self.FULL << 8, 0          # 完全ON
        else:
            on = 0                               # カウント 0 で High になり
            off = min(4095, max(1, round(duty * 4096)))  # カウント off で Low になる

        reg = self.LED0_ON_L + 4 * channel
        self.bus.write_i2c_block_data(
            self.address, reg,
            [on & 0xFF, on >> 8, off & 0xFF, off >> 8],
        )

    def set_level(self, channel, high):
        """channel を High / Low 固定にする（方向ピン用）"""
        self.set_duty(channel, 1.0 if high else 0.0)

    def all_off(self):
        """全チャンネルを完全OFF にする"""
        self._write(self.ALL_LED_ON_H, 0x00)
        self._write(self.ALL_LED_OFF_H, self.FULL)


# ============================================================
#  モータドライバ（PWM 1 本 + 方向 IN1/IN2）
# ============================================================
class MotorDriver:
    def __init__(self, pca, ch_pwm, ch_in1, ch_in2, invert=False, max_duty=1.0):
        self.pca = pca
        self.ch_pwm = ch_pwm
        self.ch_in1 = ch_in1
        self.ch_in2 = ch_in2
        self.invert = invert
        self.max_duty = max(0.0, min(1.0, max_duty))
        self.direction = 0   # 1: 正転, -1: 逆転, 0: 停止
        self.duty = 0.0      # 最後に指定したデューティ比（-1.0〜1.0）
        self.stop()

    def set_duty(self, duty):
        """
        duty: -1.0〜1.0
          正 → 正転、負 → 逆転、0 → 停止（フリー）
          実際に出力されるデューティ比は |duty| × max_duty
        """
        duty = max(-1.0, min(1.0, float(duty)))
        self.duty = duty
        if duty == 0.0:
            self.stop()
            return

        forward = (duty > 0) != self.invert
        new_dir = 1 if forward else -1

        # 方向が変わるときは、先に PWM を 0 にしてから方向ピンを切り替える
        # （切り替えの途中で一瞬だけ意図しない状態になるのを防ぐ）
        if new_dir != self.direction:
            self.pca.set_duty(self.ch_pwm, 0.0)
            self.pca.set_level(self.ch_in1, forward)
            self.pca.set_level(self.ch_in2, not forward)
            self.direction = new_dir

        self.pca.set_duty(self.ch_pwm, abs(duty) * self.max_duty)

    def stop(self, brake=False):
        """
        brake=False: フリー停止（惰性で止まる）  IN1=L, IN2=L, PWM=0
        brake=True : ブレーキ（短絡制動）        IN1=H, IN2=H, PWM=100%
          ※ TB6612 / L298N はどちらもこの組み合わせでブレーキになる
        """
        self.pca.set_duty(self.ch_pwm, 0.0)
        self.pca.set_level(self.ch_in1, brake)
        self.pca.set_level(self.ch_in2, brake)
        if brake:
            self.pca.set_duty(self.ch_pwm, 1.0)
        self.direction = 0
        self.duty = 0.0


# ============================================================
#  動作モード
# ============================================================
def ramp(motor, start, end, seconds, steps=50):
    """デューティ比を start から end まで seconds 秒かけて変化させる"""
    for i in range(1, steps + 1):
        motor.set_duty(start + (end - start) * i / steps)
        time.sleep(seconds / steps)


def run_demo(motor, peak=0.6):
    print(f"正転: 0% → {peak*100:.0f}% に加速")
    ramp(motor, 0.0, peak, 2.0)
    time.sleep(1.0)
    print("正転: 減速して停止")
    ramp(motor, peak, 0.0, 2.0)
    time.sleep(0.5)

    print(f"逆転: 0% → -{peak*100:.0f}% に加速")
    ramp(motor, 0.0, -peak, 2.0)
    time.sleep(1.0)
    print("逆転: 減速して停止")
    ramp(motor, -peak, 0.0, 2.0)

    print("ブレーキ")
    motor.stop(brake=True)
    time.sleep(0.5)
    motor.stop()
    print("デモ終了")


def run_interactive(motor):
    print("デューティ比を -100〜100 [%] で入力してください（正: 正転 / 負: 逆転）")
    print("  0 または s: 停止（フリー） / b: ブレーキ / q: 終了")
    while True:
        try:
            s = input("duty[%] > ").strip().lower()
        except EOFError:
            break

        if s in ("q", "quit", "exit"):
            break
        if s in ("", "s", "0"):
            motor.stop()
            print("  → 停止（フリー）")
            continue
        if s == "b":
            motor.stop(brake=True)
            print("  → ブレーキ")
            continue

        try:
            value = float(s)
        except ValueError:
            print("  数値、s、b、q のいずれかを入力してください")
            continue
        if not -100.0 <= value <= 100.0:
            print("  -100〜100 の範囲で入力してください")
            continue

        motor.set_duty(value / 100.0)
        actual = abs(value) * motor.max_duty
        print(f"  → {'正転' if value > 0 else '逆転'} 出力デューティ比 {actual:.1f}%")


# ============================================================
#  メイン
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="PCA9685 経由のモータ PWM 制御")
    parser.add_argument("--addr", type=lambda x: int(x, 0), default=PCA9685_ADDR,
                        help="PCA9685 の I2C アドレス（例: 0x40）")
    parser.add_argument("--freq", type=float, default=PWM_FREQ_HZ,
                        help="PWM 周波数 [Hz]（24〜1526）")
    parser.add_argument("--demo", action="store_true",
                        help="加減速のテスト動作を行う")
    args = parser.parse_args()

    # kill（SIGTERM）で終了したときも finally を通ってモータを止める
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    bus = SMBus(I2C_BUS)
    pca = None
    motor = None
    try:
        pca = PCA9685(bus, args.addr)
        try:
            freq = pca.setup(args.freq)
        except OSError:
            print(f"エラー: PCA9685（アドレス 0x{args.addr:02X}）と通信できません。")
            print("  配線、I2C の有効化、i2cdetect -y 1 の結果を確認してください。")
            pca = None
            return 1
        print(f"PCA9685 初期化完了（アドレス 0x{args.addr:02X}, PWM 約 {freq:.0f}Hz）")

        motor = MotorDriver(pca, CH_PWM, CH_IN1, CH_IN2,
                            invert=INVERT, max_duty=MAX_DUTY)

        if args.demo:
            run_demo(motor)
        else:
            run_interactive(motor)

    except KeyboardInterrupt:
        print("\n中断しました")
    finally:
        # どんな終わり方でも、最後に必ず全出力を止める
        try:
            if motor is not None:
                motor.stop()
            if pca is not None:
                pca.all_off()
                print("全出力を停止しました")
        except OSError:
            print("警告: 停止命令を送れませんでした。電源を切ってください。")
        bus.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())