from smbus2 import SMBus

bus = SMBus(1)

print(hex(bus.read_byte_data(0x40, 0x00)))