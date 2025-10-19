import pygame
import math
from typing import Tuple

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, color: Tuple[int,int,int], hover_color: Tuple[int,int,int]):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.active = True
        self.cooldown = 0.0
        self.hover_t = 0.0
        self.scale_t = 1.0
        self.press_timer = 0.0
        self.press_duration = 0.12

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        draw_color = (100,100,100) if not self.active else tuple(
            int(self.color[i] + (self.hover_color[i] - self.color[i]) * self.hover_t) for i in range(3)
        )

        w = int(self.rect.width * self.scale_t)
        h = int(self.rect.height * self.scale_t)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = self.rect.center

        pygame.draw.rect(screen, draw_color, scaled_rect, border_radius=6)
        pygame.draw.rect(screen, (255,255,255), scaled_rect, 2, border_radius=6)

        text_surf = font.render(self.text, True, (255,255,255))
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        screen.blit(text_surf, text_rect)

        if self.cooldown > 0:
            cooldown_text = font.render(f"{int(math.ceil(self.cooldown))}s", True, (255,255,0))
            screen.blit(cooldown_text, (scaled_rect.right + 5, scaled_rect.top + 5))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos) and self.active

    def update(self, dt: float):
        if self.cooldown > 0:
            self.cooldown -= dt
            self.active = False
            if self.cooldown <= 0:
                self.cooldown = 0.0
                self.active = True
        else:
            self.active = True

        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos) and self.active
        target = 1.0 if is_hover else 0.0
        lerp_speed = dt / 0.13 if 0.13 > 0 else 1.0
        self.hover_t += (target - self.hover_t) * min(1.0, lerp_speed)

        if self.press_timer > 0:
            self.press_timer = max(0.0, self.press_timer - dt)

        hover_scale = 1.0 + 0.05 * self.hover_t
        target_scale = hover_scale * (0.92 if self.press_timer > 0 else 1.0)
        self.scale_t += (target_scale - self.scale_t) * min(1.0, dt / 0.08)

    def press(self):
        self.press_timer = self.press_duration
        self.scale_t = max(0.0, self.scale_t * 0.92)