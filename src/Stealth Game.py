import pygame
import random
import math
import os
import cv2
import numpy as np
from animation import Animation
from button import Button
from guard import Guard
from particles import ParticleSystem

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
DARK_BLUE = (0, 0, 100)
DARK_GREEN = (0, 100, 0)
    
class StealthGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Terminal Infiltration")
        self.clock = pygame.time.Clock()
        self.running = True

        self.title_font = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.state = "menu"
        self.mission_time = 60
        self.time_remaining = self.mission_time
        self.detection_level = 0
        self.max_detection = 100
        self.objective_progress = 0
        self.objectives_needed = 5

        self.guards = [
            Guard(1, 8),
            Guard(2, 12),
            Guard(3, 10)
        ]
        self.load_guard_animations()

        self.create_buttons()

        self.camera_disabled = False
        self.camera_disable_time = 0
        self.lights_disabled = False
        self.lights_disable_time = 0

        self.event_timer = 0
        self.event_interval = 5
        self.current_event = None

        # Initialize background video
        self.init_background()
        
        # messages to show feedback to player
        self.feedback_messages = []

        # UI animation timer used for pulsing effects
        self.ui_time = 0.0

        # particle system
        self.particle_sys = ParticleSystem()
    
    def load_guard_animations(self):
        base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "sprites"))
        guard_anim_config = {
            'default_guard': {
                'sheet': os.path.join(base, "guard_sheet.png"),
                'frame_width': 32,
                'frame_height': 48,
                'scale': 1.0,
                'animations': {
                    'idle': {'row': 0, 'start_col': 0, 'num_frames': 4, 'speed': 0.2, 'loop': True},
                    'walk': {'row': 1, 'start_col': 0, 'num_frames': 6, 'speed': 0.1, 'loop': True},
                    'alert': {'row': 2, 'start_col': 0, 'num_frames': 4, 'speed': 0.15, 'loop': True}
                },
            }
        }

        self.guard_animation_sets = {}
        for key, info in guard_anim_config.items():
            sheet = info['sheet']
            try:
                anim_master = Animation(sheet, info['frame_width'], info['frame_height'], scale=info.get('scale', 1.0))
            except Exception as e:
                print(f"Error loading animation sheet {sheet}: {e}")
                self.guard_animation_sets[key] = {}
                continue

            anims = {}
            try:
                for name, params in info['animations'].items():
                    anim_master.add_animation(
                        name,
                        row=params['row'],
                        start_col=params.get('start_col', 0),
                        num_frames=params['num_frames'],
                        speed=params.get('speed', 0.1),
                        loop=params.get('loop', True),
                        pingpong=params.get('pingpong', False)
                    )
                    # Store the raw animation data from the master
                    anims[name] = {
                        'frames': anim_master.animations[name]['frames'],
                        'druations': anim_master.animations[name]['durations'],
                        'loop': anim_master.animations[name]['loop'],
                        'pingpong': anim_master.animations[name].get('pingpong', False)
                    }
            except Exception as e:
                print(f"load_guard_animations: failed to add animation {name}: {e}")
            # store frame data per sheet key
            self.guard_animation_sets[key] = anims
        
        # assign per guard animation instances
        default_cfg = self.guard_animation_sets.get('default_guard', None)
        if default_cfg:
            for guard in self.guards:
                guard_set = {}
                for name, data in default_cfg['anims'].items():
                    try:
                        # create a new animation instance per guard
                        anim_inst = Animation(default_cfg['sheet'], default_cfg['frame_w'], default_cfg['frame_h'], scale=default_cfg['scale'])
                        anim_inst.add_animation(name, frames=data['frames'], durations=data['durations'], loop=data.get('loop', True), pingpong=data.get('pingpong', False))
                        guard_set[name] = anim_inst
                    except Exception as e:
                        print(f"load_guard_animations: failed to instantiate animation '{name}' for guard: {e}")
                guard.animation_set = guard_set
                if 'idle' in guard.animation_set:
                    guard.current_anim_name = 'idle'
        
        # Initialize guard random phases so they don't all sync
        for guard in self.guards:
            guard.current_time = random.uniform(0, guard.patrol_time)
    
    def init_background(self):
        self.bg_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "videos", "hacking bg.mp4"))
        self.bg_cap = None
        self.bg_frame_surf = None
        try:
            self.bg_cap = cv2.VideoCapture(self.bg_path)
            if not self.bg_cap.isOpened():
                self.bg_cap = None
            else:
                ret, frame = self.bg_cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.bg_frame_surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        except Exception:
            self.bg_cap = None
            self.bg_frame_surf = None
    
    def update_background(self, dt):
        if not self.bg_cap:
            return
        ret, frame = self.bg_cap.read()
        if not ret:
            self.bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.bg_cap.read()
            if not ret:
                return
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            self.bg_frame_surf = surf
        except Exception:
            pass

    def create_buttons(self):
        button_y = 450
        button_width = 140
        button_height = 50
        spacing = 160
        start_x = 100

        self.buttons = {
            'camera': Button(start_x, button_y, button_width, button_height, "Disable Cams", DARK_BLUE, BLUE),
            'lights': Button(start_x + spacing, button_y, button_width, button_height, "Cut Lights", DARK_BLUE, BLUE),
            'distract': Button(start_x + 2 * spacing, button_y, button_width, button_height, "Distraction", DARK_BLUE, BLUE),
            'hack': Button(start_x + 3 * spacing, button_y, button_width, button_height, "Hack System", DARK_GREEN, GREEN),
            'menu': Button(WIDTH//2 - 100, HEIGHT//2 + 100, 200, 50, "START MISSION", DARK_GREEN, GREEN)
        }

    def reset_game(self):
        self.time_remaining = self.mission_time
        self.detection_level = 0
        self.objective_progress = 0
        self.camera_disabled = False
        self.camera_disable_time = 0
        self.lights_disabled = False
        self.lights_disable_time = 0
        self.event_timer = 0
        self.current_event = None
        for guard in self.guards:
            guard.alert = False
            guard.current_time = random.uniform(0, guard.patrol_time)
        self.create_buttons()
        self.particle_sys.clear()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if self.state == "menu":
                    if self.buttons['menu'].is_clicked(pos):
                        self.reset_game()
                        self.state = "playing"
                    
                elif self.state == "playing":
                    self.handle_game_clicks(pos)
                
                elif self.state in ["success", "failure"]:
                    if self.buttons['menu'].is_clicked(pos):
                        self.reset_game()
                        self.state = "menu"
        
    def handle_game_clicks(self, pos):
        if self.buttons['camera'].is_clicked(pos):
            self.buttons['camera'].press()
            self.camera_disabled = True
            self.camera_disable_time = 8
            self.buttons['camera'].cooldown = 7
            delta = -15
            self.detection_level = max(0, self.detection_level + delta)
            # smoke effect at button and floating text
            bx, by = self.buttons['camera'].rect.center
            self.particle_sys.spawn_smoke(bx, by, count=12)
            self.particle_sys.add_detection_popup(delta, bx, by)

        elif self.buttons['lights'].is_clicked(pos):
            self.buttons['lights'].press()
            self.lights_disabled = True
            self.lights_disable_time = 6
            self.buttons['lights'].cooldown = 5
            delta = -10
            self.detection_level = max(0, self.detection_level + delta)
            lx, ly = self.buttons['lights'].rect.center
            self.particle_sys.spawn_smoke(lx, ly, count=8)
            self.particle_sys.add_detection_popup(delta, lx, ly)
        
        elif self.buttons['distract'].is_clicked(pos):
            self.buttons['distract'].press()
            for guard in self.guards:
                guard.alert = False
            delta = -20
            self.detection_level = max(0, self.detection_level + delta)
            dx, dy = self.buttons['distract'].rect.center
            self.particle_sys.spawn_smoke(dx, dy, count=14)
            self.particle_sys.add_detection_popup(delta, dx, dy)
            self.buttons['distract'].cooldown = 10
        
        elif self.buttons['hack'].is_clicked(pos):
            self.buttons['hack'].press()
            success_chance = max(0.15, 1.0 - (self.detection_level / 80.0))
            if random.random() < success_chance:
                self.objective_progress += 1
                delta = -5
                self.detection_level = max(0, self.detection_level + delta)
                self.buttons['hack'].cooldown = 2.0
                self.feedback_messages.append({'text': "HACK SUCCESSFUL", 'color': GREEN, 'time': 2.5})
                hx, hy = WIDTH//2, 220
                self.particle_sys.spawn_sparks(hx, hy, count=18, color=(255,220,120))
                self.particle_sys.add_detection_popup(delta, hx, hy)
                self.particle_sys.start_shake(3.0, 0.25)
            else:
                penalty = min(20, int(8 + self.detection_level * 0.05))
                self.detection_level += penalty
                self.buttons['hack'].cooldown = 3.5
                self.feedback_messages.append({'text': "HACK FAILED", 'color': RED, 'time': 2.5})
                hx, hy = WIDTH//2, 220
                self.particle_sys.spawn_sparks(hx, hy, count=26, color=(255,80,60))
                self.particle_sys.add_detection_popup(+penalty, hx, hy)
                self.particle_sys.start_shake(8.0, 0.4)

    def update(self, dt):
        if self.state != "playing":
            return

        self.time_remaining -= dt
        # advance UI timer for pulsing effects
        self.ui_time += dt

        for button in self.buttons.values():
            button.update(dt)
        
        if self.camera_disable_time > 0:
            self.camera_disable_time -= dt
        else:
            self.camera_disabled = False
        
        if self.lights_disable_time > 0:
            self.lights_disable_time -= dt
        else:
            self.lights_disabled = False
        
        for guard in self.guards:
            guard.update(dt)
        
        base_detection = 2 * dt
        if self.camera_disabled:
            base_detection *= 0.3
        if self.lights_disabled:
            base_detection *= 0.5
        
        self.detection_level += base_detection

        for guard in self.guards:
            if 0.4 < guard.position < 0.6:
                detection_chance = 0.02
                if not self.lights_disabled:
                    detection_chance *= 2
                if not self.camera_disabled:
                    detection_chance *= 1.5
                
                if random.random() < detection_chance:
                    guard.alert = True
                    delta = 5
                    self.detection_level += delta
                    # pop up near guard position
                    gx = 100 + int(guard.position * 800)
                    gy = 150 + (self.guards.index(guard) * 60) + 20
                    self.particle_sys.spawn_sparks(gx, gy, count=6, color=(255,180,80))
                    self.particle_sys.add_detection_popup(+delta, gx, gy)
        
        self.event_timer += dt
        if self.event_timer >= self.event_interval:
            self.event_timer = 0
            self.trigger_random_event()
        
        if isinstance(self.current_event, dict):
            dps = self.current_event.get('dps', 0)
            if dps:
                self.detection_level += dps * dt
            self.current_event['time_left'] -= dt
            if self.current_event['time_left'] <= 0:
                self.current_event = None
        
        # update particle system
        self.particle_sys.update(dt)
        
        for m in list(self.feedback_messages):
            m['time'] -= dt
            if m['time'] <= 0:
                self.feedback_messages.remove(m)

        self.detection_level = max(0, min(self.detection_level, self.max_detection))
        if self.objective_progress >= self.objectives_needed:
            self.state = "success"
            self.particle_sys.clear()
        elif self.detection_level >= self.max_detection or self.time_remaining <= 0:
            self.state = "failure"
            self.particle_sys.clear()
        
    def trigger_random_event(self):
        events = [
            {'text': "Security sweep initiated", 'duration': 6.0, 'instant': random.randint(5, 12), 'dps': 1.0},
            {'text': "Guard shift change", 'duration': 8.0, 'instant': 0, 'dps': 0.5},
            {'text': "System scan detected", 'duration': 5.0, 'instant': random.randint(8, 16), 'dps': 1.5},
            {'text': "Patrol route adjusted", 'duration': 10.0, 'instant': 0, 'dps': 0.3},
            ]
        ev = random.choice(events)
        inst = ev.get('instant', 0)
        if inst:
            ex, ey = WIDTH//2, 200
            self.particle_sys.spawn_sparks(ex, ey, count=18, color=(255,200,140))
            self.particle_sys.add_detection_popup(+inst, ex, ey)
        self.detection_level += inst
        ev['time_left'] = ev['duration']
        self.current_event = ev
        # screen shake for big events
        if inst >= 10:
            self.particle_sys.start_shake(9.0, 0.5)
    
    def draw(self):
        # render everything to a temp canva so we can blit screen shake offset
        canvas = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
        canvas.fill((0,0,0))
        old_screen = self.screen
        self.screen = canvas
        if self.bg_frame_surf:
            bg = pygame.transform.scale(self.bg_frame_surf, (WIDTH, HEIGHT))
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(BLACK)

        self.particle_sys.draw_particles(self.screen)

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "success":
            self.draw_end_screen("MISSION SUCCESS", GREEN)
        elif self.state == "failure":
            self.draw_end_screen("MISSION FAILED", RED)

        # Shake offset
        ox, oy = self.particle_sys.get_shake_offset()
        
        self.particle_sys.draw_float_texts(self.screen, self.font)

        # restore screen and blit canvas with offset
        self.screen = old_screen
        self.screen.fill(BLACK)
        self.screen.blit(canvas, (ox, oy))
        pygame.display.flip()
    
    def draw_menu(self):
        title = self.title_font.render("Terminal Infiltration", True, GREEN)
        title_rect = title.get_rect(center=(WIDTH//2, 150))
        self.screen.blit(title, title_rect)

        instructions = [
            "Your agent is infiltrating a secure facility.",
            "Use the terminal to help them avoid detection.",
            "Complete 5 hacks before time runs out.",
            "Don't let the detection reach 100%!"
        ]

        y = 250
        for line in instructions:
            text = self.font.render(line, True, WHITE)
            text_rect = text.get_rect(center=(WIDTH//2, y))
            self.screen.blit(text, text_rect)
            y += 40

        self.buttons['menu'].draw(self.screen, self.font)

    def draw_game(self):
        title = self.title_font.render("SECURITY TERMINAL", True, GREEN)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))

        self.draw_status_bars(100, 90, 300, 30, "TIME", self.time_remaining, self.mission_time, BLUE)
        self.draw_status_bars(WIDTH - 400, 90, 300, 30, "DETECTION", self.detection_level, self.max_detection, RED)

        obj_text = self.font.render(f"Objectives: {self.objective_progress}/{self.objectives_needed}", True, GREEN)
        self.screen.blit(obj_text, (WIDTH//2 - obj_text.get_width()//2, 90))

        for i, msg in enumerate(self.feedback_messages):
            txt = self.font.render(msg['text'], True, msg['color'])
            txt_rect = txt.get_rect(center=(WIDTH//2, 130 + i * 30))
            self.screen.blit(txt, txt_rect)

        monitor_y = 150
        for i, guard in enumerate(self.guards):
            guard.draw(self.screen, 100, monitor_y + i * 60, 800, 40)

        status_y = 350
        systems = [
            ("CAMERAS", "OFFLINE" if self.camera_disabled else "ONLINE", GREEN if self.camera_disabled else RED),
            ("LIGHTS", "OFFLINE" if self.lights_disabled else "ONLINE", GREEN if self.lights_disabled else RED)
        ]

        for i, (name, status, color) in enumerate(systems):
            text = self.small_font.render(f"{name}: {status}", True, color)
            self.screen.blit(text, (100 + i * 250, status_y))

        if self.current_event:
            ev_text = self.current_event['text'] if isinstance(self.current_event, dict) else str(self.current_event)
            event_text = self.small_font.render(f"! {ev_text}", True, YELLOW)
            self.screen.blit(event_text, (WIDTH//2 - event_text.get_width()//2, 390))

        for key in ['camera', 'lights', 'distract', 'hack']:
            self.buttons[key].draw(self.screen, self.small_font)
        
    def draw_status_bars(self, x, y, width, height, label, value, max_value, color):
        label_text = self.small_font.render(label, True, WHITE)
        self.screen.blit(label_text, (x, y - 25))

        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, width, height))

        if max_value <= 0:
            fill_width = 0
        else:
            fill_width = int((value / max_value) * width)
        fill_width = max(0, min(fill_width, width))
        # pulsing effect for detection bar when high
        draw_color = color
        if max_value > 0:
            if label == "DETECTION":
                ratio = value / max_value
                if ratio >= 0.6:
                    # pulse period around 0.6s, amplitude small
                    period = 0.6
                    pulse = 0.5 * (1.0 + math.sin(2 * math.pi * (self.ui_time / period)))
                    amp = 0.45
                    draw_color = tuple(
                        min(255, int(c + (255 - c) * pulse * amp))
                        for c in color
                    )
            elif label == "TIME":
                ratio = value / max_value
                if ratio <= 0.3:
                    period = 0.6
                    pulse = 0.5 * (1.0 + math.sin(2 * math.pi * (self.ui_time / period)))
                    amp = 0.45
                    target = (255, 200, 40)
                    draw_color = tuple(
                        min(255, int(c + (t - c) * pulse * amp))
                        for c, t in zip(color, target)
                    )
        pygame.draw.rect(self.screen, draw_color, (x, y, fill_width, height))

        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        value_text = self.small_font.render(f"{int(value)}/{max_value}", True, WHITE)
        self.screen.blit(value_text, (x + width//2 - value_text.get_width()//2, y + height//2 - value_text.get_height()//2))

    def draw_end_screen(self, message, color):
        text = self.title_font.render(message, True, color)
        text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        self.screen.blit(text, text_rect)

        stats = [
            f"Objectives Completed: {self.objective_progress}/{self.objectives_needed}",
            f"Final Detection: {int(self.detection_level)}%",
            f"Time Remaining: {int(self.time_remaining)}s"
        ]

        y = HEIGHT//2
        for stat in stats:
            stat_text = self.font.render(stat, True, WHITE)
            stat_rect = stat_text.get_rect(center=(WIDTH//2, y))
            self.screen.blit(stat_text, stat_rect)
            y += 40
        
        self.buttons['menu'].text = "RETURN TO MENU"
        self.buttons['menu'].draw(self.screen, self.font)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self.update_background(dt)

            self.handle_events()
            self.update(dt)
            self.draw()
        
        if self.bg_cap:
            try:
                self.bg_cap.release()
            except Exception:
                pass
        
        pygame.quit()

if __name__ == "__main__":
    game = StealthGame()
    game.run()