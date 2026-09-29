import pygame
"""
data = {
     "Rem": controller0.right_y,
    　"Lam": controller0.left_y
            }
"""

class Controller:

    def __init__(self, number):

        pygame.init()
        pygame.joystick.init()

        self.joystick = pygame.joystick.Joystick(number)
        self.joystick.init()

        self.left_x = 0
        self.left_y = 0
        self.right_x = 0
        self.right_y = 0

    def read(self):#y軸前が正にしてるよ
        pygame.event.pump()

        self.left_x = round(self.joystick.get_axis(0), 1)
        self.left_y = -round(self.joystick.get_axis(1), 1)
        self.right_x = round(self.joystick.get_axis(3), 1)
        self.right_y = -round(self.joystick.get_axis(4), 1)

    def exit(self):
        self.joystick.quit()

