import pygame
import os
from slider import Slider

class SettingsMenu:
    def __init__(self, width, height, audio_manager, button_class):
        self.width = width
        self.height = height
        self.audio_manager = audio_manager
        self.visible = False

        # Panel
        panel_width, panel_height = 400, 300
        panel_x = (width - panel_width) // 2
        panel_y = (height - panel_height) // 2
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # Sliders
        slider_x = panel_x + 50
        volumes = self.audio_manager.get_volumes()

        self.sliders = {
            'master': Slider(slider_x, panel_y + 80, 300, 20, 0.0, 1.0, 
                             volumes['master'], "Master Volume", self.audio_manager.set_master_volume),
            'music': Slider(slider_x, panel_y + 130, 300, 20, 0.0, 1.0, 
                            volumes['music'], "Music Volume", self.audio_manager.set_music_volume),
            'sfx': Slider(slider_x, panel_y + 180, 300, 20, 0.0, 1.0, 
                          volumes['sfx'], "SFX Volume", self.audio_manager.set_sfx_volume),
        }

        self.close_button = button_class(panel_x + panel_width - 80, panel_y + panel_height - 50,
                                         60, 30, "CLOSE", (100, 100, 100), (150, 150, 150))
    
    def show(self):
        self.visible = True
        volumes = self.audio_manager.get_volumes()
        for key, slider in self.sliders.items():
            slider.value = volumes[key]
            slider.update_handle_pos()
    
    def hide(self):
        self.visible = False
    
    def handle_event(self, event):
        if not self.visible:
            return False
        
        for slider in self.sliders.values():
            slider.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.is_clicked(event.pos):
                self.close_button.press()
                self.audio_manager.play_sfx("button_click")
                self.hide()
                return True
            elif self.panel_rect.collidepoint(event.pos):
                return True
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        
        return self.visible
    
    def update(self, dt):
        if self.visible:
            mouse_pos = pygame.mouse.get_pos()
            self.close_button.update(dt)
        
    def draw(self, screen, font):
        if not self.visible:
            return
        
        # Background
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Draw panel
        pygame.draw.rect(screen, (30, 30, 30), self.panel_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 100), self.panel_rect, 2, border_radius=10)

        # Draw title
        title = font.render("SETTINGS", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.panel_rect.centerx, self.panel_rect.y + 40))
        screen.blit(title, title_rect)

        # Draw sliders
        for slider in self.sliders.values():
            slider.draw(screen, font)

        # Draw close button
        self.close_button.draw(screen, font)