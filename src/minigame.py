import pygame
import random
import math
import time

class Minigame:
    def __init__(self, width, height, difficulty='normal'):
        self.width = width
        self.height = height
        self.difficulty = difficulty
        self.active = False
        self.complete = False
        self.success_count = 0
        self.fail_count = 0
        self.round_num = 0
    
    def start(self):
        self.active = True
        self.complete = False
        self.success_count = 0
        self.fail_count = 0
        self.round_num = 0
    
    def update(self, dt):
        pass

    def draw(self, surface):
        pass

    def handle_input(self, event):
        pass

    def is_complete(self):
        return self.complete
    
    def get_result(self):
        """"""
        total = self.success_count + self.fail_count
        if total == 0:
            return (False 20)
        success_rate = self.success_count / total
        if success_rate >= 0.7:
            return (True, -int(success_rate * 15))
        else:
            return (False, int((1 - success_rate) * 20))
