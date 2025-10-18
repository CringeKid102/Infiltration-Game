import pygame
import random
import math
import os
import cv2
import numpy as np
from animation import Animation

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

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.active = True
        self.cooldown = 0
        self.hover_t = 0.0
        self.scale_t = 1.0
        self.press_timer = 0.0
        self.press_duration = 0.12
    
    def draw(self, screen, font):
        draw_color = self.color
        if not self.active:
            draw_color = GRAY
        else:
            draw_color = tuple(
                int(self.color[i] + (self.hover_color[i] - self.color[i]) * self.hover_t)
                for i in range(3)
            )
        
        w = int(self.rect.width * self.scale_t)
        h = int(self.rect.height * self.scale_t)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = self.rect.center

        pygame.draw.rect(screen, draw_color, scaled_rect, border_radius=6)
        pygame.draw.rect(screen, WHITE, scaled_rect, 2, border_radius=6)

        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        screen.blit(text_surf, text_rect)

        if self.cooldown > 0:
            cooldown_text = font.render(f"{int(math.ceil(self.cooldown))}s", True, YELLOW)
            screen.blit(cooldown_text, (scaled_rect.right + 5, scaled_rect.top + 5))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos) and self.active

    def update(self, dt):
        if self.cooldown > 0:
            self.cooldown -= dt
            self.active = False
            if self.cooldown <= 0:
                self.cooldown = 0
                self.active = True
        else:
            self.active = True
            self.cooldown = 0
        
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos) and self.active
        target = 1.0 if is_hover else 0.0
        lerp_speed = dt / 0.13 if 0.12 > 0 else 1.0
        self.hover_t += (target - self.hover_t) * min(1.0, lerp_speed)

        if self.press_timer > 0:
            self.press_timer = max(0.0, self.press_timer - dt)
        hover_scale = 1.0 + 0.05 * self.hover_t
        if self.press_timer > 0:
            target_scale =  hover_scale * 0.92
        else:
            target_scale = hover_scale
        self.scale_t += (target_scale - self.scale_t) * min(1.0, dt / 0.08)

    def press(self):
        """
        Call when button is activated to play press animation.
        """
        self.press_timer = self.press_duration
        self.scale_t = max(0.0, self.scale_t * 0.92)

class Guard:
    def __init__(self, patrol_id, patrol_time, animation_set: dict = None, default_anim: str = "idle"):
        self.id = patrol_id
        self.patrol_time = patrol_time
        self.current_time = 0
        self.position = 0
        self.alert = False

        # animation_set
        self.animation_set = animation_set or {}
        self.current_anim_name = default_anim if default_anim in self.animation_set else None
        self.anim_offset_x = 0
        self.anim_offset_y = 0

    def update(self, dt):
        self.current_time += dt
        self.position = (self.current_time % self.patrol_time) / self.patrol_time

        # update animation
        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            # set alert animation
            if self.alert and "alert" in self.animation_set and self.current_anim_name != "alert":
                anim = self.animation_set["alert"]
                self.current_anim_name = "alert"
            elif not self.alert and self.current_anim_name == "alert" and "idle" in self.animation_set:
                self.current_anim_name = "idle"
                anim = self.animation_set["idle"]
            anim.update(dt)
    
    def draw(self, screen, x, y, width, height):
        route_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, DARK_GRAY, route_rect)
        pygame.draw.rect(screen, WHITE, route_rect, 1)

        guard_x = x + int(self.position * width)
        anim = self.animation_set.get(self.current_anim_name) if self.current_anim_name else None
        if anim:
            anim.draw(screen, guard_x + self.anim_offset_x, y + height//2 + self.anim_offset_y, anchor="center")
        else:
            guard_color = RED if self.alert else BLUE
            pygame.draw.circle(screen, guard_color, (guard_x, y + height//2), height//3)

        font = pygame.font.Font(None, 20)
        label = font.render(f"Guard {self.id}", True, WHITE)
        screen.blit(label, (x, y - 20))
    
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

        # Particle system and floating text for detection changes
        self.particles = [] # List of dicts: {x, y, vx, vy, life, size, oclor, type}
        self.float_texts = [] # List of dicts: {text, x, y, vy, time, color, alpha}

        # Screen shake
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0
    
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
            for name, params in info['animations'].items():
                try:
                    anim_master.add_animation(
                        name,
                        params['row'],
                        params.get('start_col', 0),
                        params['num_frames'],
                        speed=params.get('speed', 0.1),
                        loop=params.get('loop', True)
                    )
                    anims[name] = anim_master
                except Exception as e:
                    print(f"load_guard_animations: failed to add animation {name}: {e}")
            self.guard_animation_sets[key] = anims
        
        for guard in self.guards:
            guard.animation_set = self.guard_animation_sets.get('default_guard', {})
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
        self.particles.clear()
        self.float_texts.clear()
        self.shake_amount = 0.0
        self.shake_time = 0.0
        self.shake_duration = 0.0

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
            self.spawn_smoke(bx, by, count=12)
            self.add_detection_popup(delta, bx, by)

        elif self.buttons['lights'].is_clicked(pos):
            self.buttons['lights'].press()
            self.lights_disabled = True
            self.lights_disable_time = 6
            self.buttons['lights'].cooldown = 5
            delta = -10
            self.detection_level = max(0, self.detection_level + delta)
            lx, ly = self.buttons['lights'].rect.center
            self.spawn_smoke(lx, ly, count=8)
            self.add_detection_popup(delta, lx, ly)
        
        elif self.buttons['distract'].is_clicked(pos):
            self.buttons['distract'].press()
            for guard in self.guards:
                guard.alert = False
            delta = -20
            self.detection_level = max(0, self.detection_level + delta)
            dx, dy = self.buttons['distract'].rect.center
            self.spawn_smoke(dx, dy, count=14)
            self.add_detection_popup(delta, dx, dy)
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
                self.spawn_sparks(hx, hy, count=18, color=(255,220,120))
                self.add_detection_popup(delta, hx, hy)
                self.shake_amount = max(self.shake_amount, 3.0)
                self.shake_time = self.shake_duration = 0.25
            else:
                penalty = min(20, int(8 + self.detection_level * 0.05))
                self.detection_level += penalty
                self.buttons['hack'].cooldown = 3.5
                self.feedback_messages.append({'text': "HACK FAILED", 'color': RED, 'time': 2.5})
                hx, hy = WIDTH//2, 220
                self.spawn_sparks(hx, hy, count=26, color=(255,80,60))
                self.add_detection_popup(+penalty, hx, hy)
                self.shake_amount = max(self.shake_amount, 8.0)
                self.shake_time = self.shake_duration = 0.4

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
                    self.spawn_sparks(gx, gy, count=6, color=(255,180,80))
                    self.add_detection_popup(+delta, gx, gy)
        
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
        
        # update particles
        for p in list(self.particles):
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += p.get('gravity', 0) * dt
            p['life'] -= dt
            if p['life'] <= 0:
                self.particles.remove(p)
        
        # update floating texts
        for ft in list(self.float_texts):
            ft['y'] += ft['vy'] * dt
            ft['time'] -= dt
            ft['alpha'] = max(0, int(255 * (ft['time'] / max(0.01, ft.get('duration', 1.0)))))
            if ft['time'] <= 0:
                self.float_texts.remove(ft)
        
        # decay screen shake
        if self.shake_time > 0:
            self.shake_time -= dt
            if self.shake_time <= 0:
                self.shake_amount = 0.0
                self.shake_time = 0.0
                self.shake_duration = 0.0
        else:
            self.shake_amount = max(0.0, self.shake_amount - 8.0 * dt)
        
        for m in list(self.feedback_messages):
            m['time'] -= dt
            if m['time'] <= 0:
                self.feedback_messages.remove(m)

        self.detection_level = max(0, min(self.detection_level, self.max_detection))
        if self.objective_progress >= self.objectives_needed:
            self.state = "success"
            self.particles.clear()
            self.float_texts.clear()
        elif self.detection_level >= self.max_detection or self.time_remaining <= 0:
            self.state = "failure"
            self.particles.clear()
            self.float_texts.clear()
        
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
            self.spawn_sparks(ex, ey, count=18, color=(255,200,140))
            self.add_detection_popup(+inst, ex, ey)
        self.detection_level += inst
        ev['time_left'] = ev['duration']
        self.current_event = ev
        # screen shake for big events
        if inst >= 10:
            self.shake_amount = max(self.shake_amount, 9.0)
            self.shake_time = self.shake_duration = 0.5
    
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

        self.draw_particles(self.screen)

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "success":
            self.draw_end_screen("MISSION SUCCESS", GREEN)
        elif self.state == "failure":
            self.draw_end_screen("MISSION FAILED", RED)
        
        self.draw_float_texts(self.screen)

        # Shake offset
        ox, oy = 0, 0
        if self.shake_amount > 0:
            frac = (self.shake_time / max(0.0001, self.shake_duration)) if self.shake_duration > 0 else 0
            cur_amp = self.shake_amount * (frac if frac > 0 else 1.0)
            ox = int(random.uniform(-cur_amp, cur_amp))
            oy = int(random.uniform(-cur_amp, cur_amp))
        
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
                    target = (355, 200, 40)
                    draw_color = tuple(
                        min(255, int(c + (t - c) * pulse * amp))
                        for c, t in zip(color, target)
                    )
        pygame.draw.rect(self.screen, draw_color, (x, y, fill_width, height))

        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        value_text = self.small_font.render(f"{int(value)}/{max_value}", True, WHITE)
        self.screen.blit(value_text, (x + width//2 - value_text.get_width()//2, y + height//2 - value_text.get_height()//2))

    def spawn_sparks(self, x, y, count=12, color=(255,200,100)):
        for i in range(count):
            ang = random.uniform(0, math.pi*2)
            spd = random.uniform(40, 220)
            life = random.uniform(0.35, 0.9)
            self.particles.append({
                'x': x + random.uniform(-8, 8),
                'y': y + random.uniform(-8, 8),
                'vx': math.cos(ang) * spd,
                'vy': math.sin(ang) * spd * 0.6 - random.uniform(10, 60),
                'life': life,
                'inital_life': life,
                'size': random.uniform(2, 4),
                'color': color,
                'gravity': 300,
                'type': 'spark'
            })

    def spawn_smoke(self, x, y, count=10):
        for i in range(count):
            life = random.uniform(0.9, 2.0)
            self.particles.append({
                'x': x + random.uniform(-12, 12),
                'y': y + random.uniform(-6, 6),
                'vx': random.uniform(-20, 20),
                'vy': random.uniform(-40, 10),
                'life': life,
                'inital_life': life,
                'size': random.uniform(8, 18),
                'color': (180, 180, 180),
                'gravity': -20,
                'type': 'smoke'
            })
    
    def add_detection_popup(self, delta, x=None, y=None):
        if x is None or y is None:
            x, y = WIDTH//2, 200
        txt = f"{'+' if delta>0 else ''}{int(delta)}"
        col = RED if delta > 0 else GREEN
        self.float_texts.append({
            'text': txt,
            'x': x + random.uniform(-12, 12),
            'y': y + random.uniform(-6, 6),
            'vy': -40 - random.uniform(0, 40),
            'time': 1.0,
            'duration': 1.0,
            'color': col,
            'alpha': 255,
        })
    
    def draw_particles(self, surface):
        for p in self.particles:
            life_frac = max(0.0, min(1.0, p['life'] / max(0.001, p.get('initial_life', p['life']))))
            alpha = int(255 * life_frac)
            if p['type'] == 'spark':
                r = max(1, int(p['size']))
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                col = p['color'] + (alpha,)
                pygame.draw.circle(s, col, (r, r), r)
                surface.blit(s, (int(p['x'])-r, int(p['y'])-r))
            else:
                r = max(1, int(p['size']))
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                sc = p['color'] + (max(20, int(150 * life_frac)),)
                pygame.draw.circle(s, sc, (r, r), r)
                surface.blit(s, (int(p['x'])-r, int(p['y'])-r))
    
    def draw_float_texts(self, surface):
        for ft in self.float_texts:
            txt_surf = self.font.render(ft['text'], True, ft['color'])
            txt_surf.set_alpha(ft.get('alpha', 255))
            surface.blit(txt_surf, (int(ft['x']), int(ft['y'])))

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