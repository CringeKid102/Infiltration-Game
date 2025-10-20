import pygame
import math
from typing import Tuple, Optional

class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, color: Tuple[int,int,int], hover_color: Tuple[int,int,int],
                 tooltip: str = "", icon: Optional[pygame.Surface] = None, hotkey: str = ""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.tooltip = tooltip
        self.icon = icon
        self.hotkey = hotkey
        self.active = True
        self.cooldown = 0.0
        self.max_cooldown = 0.0
        self.hover_t = 0.0
        self.scale_t = 1.0
        self.press_timer = 0.0
        self.press_duration = 0.12

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, show_tooltip: bool = False):
        draw_color = (100,100,100) if not self.active else tuple(
            int(self.color[i] + (self.hover_color[i] - self.color[i]) * self.hover_t) for i in range(3)
        )

        w = int(self.rect.width * self.scale_t)
        h = int(self.rect.height * self.scale_t)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = self.rect.center

        pygame.draw.rect(screen, draw_color, scaled_rect, border_radius=6)
        pygame.draw.rect(screen, (255,255,255), scaled_rect, 2, border_radius=6)

        if self.cooldown > 0 and self.max_cooldown > 0:
            self._draw_radial_cooldown(screen, scaled_rect)
        
        if self.icon:
            icon_rect = self.icon.get_rect(center=scaled_rect.center)
            screen.blit(self.icon, icon_rect)

        text_surf = font.render(self.text, True, (255,255,255))
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        screen.blit(text_surf, text_rect)

        if self.hotkey:
            small_font = pygame.font.Font(None, 18)
            key_surf = small_font.render(self.hotkey, True, (200,200,200))
            screen.blit(key_surf, (scaled_rect.left + 4, scaled_rect.top + 4))
        
        if show_tooltip and self.tooltip:
            self._draw_tooltip(screen, font)
    
    def _draw_radial_cooldown(self, screen: pygame.Surface, rect: pygame.Rect):
        """
        Draw a radial cooldown overlay on the button.
        """
        progress = 1.0 - (self.cooldown / self.max_cooldown)
        center = rect.center
        radius = min(rect.width, rect.height) // 2 - 4

        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        if progress < 1.0:
            points = [center]
            start_angle = -math.pi / 2
            end_angle = start_angle + (2 * math.pi * progress)

            steps = 32
            for i in range(steps + 1):
                angle = start_angle + (end_angle - start_angle) * (i / steps)
                x = center[0] + radius * math.cos(angle) - rect.left
                y = center[1] + radius * math.sin(angle) - rect.top
                points.append((x, y))
            
            if len(points) > 2:
                pygame.draw.polygon(overlay, (0, 0, 0, 160), points)
            
        screen.blit(overlay, rect.topleft)

        cooldown_font = pygame.font.Font(None, 24)
        cd_text = cooldown_font.render(f"{int(math.ceil(self.cooldown))}", True, (255,255,0))
        cd_rect = cd_text.get_rect(center=rect.center)
        screen.blit(cd_text, cd_rect)

    def _draw_tooltip(self, screen: pygame.Surface, font: pygame.font.Font):
        """
        Draw the tooltip near the button.
        """
        tooltip_font = pygame.font.Font(None, 20)
        lines = self.tooltip.split('\n')

        max_width = max(tooltip_font.size(line)[0] for line in lines)
        line_height = tooltip_font.get_linesize()
        padding = 8

        tooltip_rect = pygame.Rect(
            self.rect.centerx - max_width // 2 - padding,
            self.rect.bottom + 10,
            max_width + padding * 2,
            line_height * len(lines) + padding * 2
        )

        pygame.draw.rect(screen, (40,40,40), tooltip_rect, border_radius=4)
        pygame.draw.rect(screen, (200,200,200), tooltip_rect, 1, border_radius=4)

        y = tooltip_rect.top + padding
        for line in lines:
            text_surf = tooltip_font.render(line, True, (255,255,255))
            screen.blit(text_surf, (tooltip_rect.left + padding, y))
            y += line_height

    def update(self, dt: float):
        if self.cooldown > 0:
            self.cooldown -= dt
            self.active = False
            if self.cooldown <= 0:
                self.cooldown = 0.0
                self.max_cooldown = 0.0
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

    def is_hovered(self):
        """
        Check if the button is currently hovered.
        """
        mouse_pos = pygame.mouse.get_pos()
        return self.rect.collidepoint(mouse_pos) and self.active

    def press(self):
        self.press_timer = self.press_duration
        self.scale_t = max(0.0, self.scale_t * 0.92)
    
    def set_cooldown(self, cooldown_time: float):
        """
        Set the button's cooldown.
        """
        self.cooldown = cooldown_time
        self.max_cooldown = cooldown_time