from smbus2 import SMBus

bus = SMBus(1)#バスは1以外もあるけどSDA,SCLのバスは1しかないので1を指定する

mode1 = bus.read_byte_data(0x40, 0x00)#0x40はアドレス、0x00はレジスタのアドレスを指定している。レジスタのアドレスはデータシートに書いてある。

print("before =", hex(mode1))#hexで16進数に

bus.write_byte_data(
    0x40,
    0x00,
    mode1 & ~0x10
)#~はnot

mode1 = bus.read_byte_data(0x40, 0x00)

print("after =", hex(mode1))