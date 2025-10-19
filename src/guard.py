import pygame
from typing import Optional, Dict
from animation import Animation

class Guard:
    def __init__(self, patrol_id: int, patrol_time: float, animation_set: Dict[str, Animation] = None, default_anim: str = "idle"):
        self.id = patrol_id
        self.patrol_time = patrol_time
        self.current_time = 0.0
        self.position = 0.0
        self.alert = False

        self.animation_set = animation_set or {}
        self.current_anim_name = default_anim if default_anim in self.animation_set else None
        self.anim_offset_x = 0
        self.anim_offset_y = 0

    def update(self, dt: float):
        self.current_time += dt
        self.position = (self.current_time % self.patrol_time) / self.patrol_time

        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            if self.alert and "alert" in self.animation_set and self.current_anim_name != "alert":
                anim = self.animation_set["alert"]
                self.current_anim_name = "alert"
            elif not self.alert and self.current_anim_name == "alert" and "idle" in self.animation_set:
                self.current_anim_name = "idle"
                anim = self.animation_set["idle"]
            anim.update(dt)

    def draw(self, screen: pygame.Surface, x: int, y: int, width: int, height: int):
        route_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (50,50,50), route_rect)
        pygame.draw.rect(screen, (255,255,255), route_rect, 1)

        guard_x = x + int(self.position * width)
        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            anim.draw(screen, guard_x + self.anim_offset_x, y + height//2 + self.anim_offset_y, anchor="center")
        else:
            guard_color = (255,0,0) if self.alert else (0,0,255)
            pygame.draw.circle(screen, guard_color, (guard_x, y + height//2), 8)

        font = pygame.font.Font(None, 20)
        label = font.render(f"Guard {self.id}", True, (255,255,255))
        screen.blit(label, (x, y - 20))