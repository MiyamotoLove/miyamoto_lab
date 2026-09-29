import pygame

def pygame_start():
    pygame.init()
    pygame.joystick.init()

def pygame_stop():
    pygame.quit()

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
        self.left_y = round(self.joystick.get_axis(1) , 1)
        self.right_x = round(self.joystick.get_axis(2) , 1)
        self.right_y = round(self.joystick.get_axis(3) ,1 )

    def exit(self):
        self.joystick.quit()


def main():
    pygame_start()
    try:
        while True:
            controller0 = Controller(0)
            controller0.read()
            print(
                f"\r"
                f"左: Y={controller0.left_y}"
                f"右: Y={controller0.right_y}",
                end=""
            )
    except KeyboardInterrupt:
        print("\n終了")
    finally:
        controller0.exit()
        pygame_stop()

if __name__ == "__main__": # test
    main()