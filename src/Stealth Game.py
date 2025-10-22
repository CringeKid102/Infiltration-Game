import pygame
import random
import math
import os
import cv2
from animation import Animation
from button import Button
from guard import Guard
from particles import ParticleSystem
from transition import TransitionManager, TransitionType

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
        """
        Initialize the game.
        """
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Terminal Infiltration")
        self.clock = pygame.time.Clock()
        self.running = True

        # Reusable render canvas to avoid reallocating each frame
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()

        # Initialize fonts
        self.title_font = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.state = "menu"
        self._load_icons()
        
        # Game parameters
        self.mission_time = 60
        self.time_remaining = self.mission_time
        self.detection_level = 0
        self.max_detection = 100
        self.objective_progress = 0
        self.objectives_needed = 5

        # Smooth animated values
        self.animated_time = self.mission_time
        self.animated_detection = 0.0
        self.animated_objectives = 0.0

        # Camera blink animation
        self.camera_blink_time = 0.0
        self.camera_blink_active = False

        self.guards = [
            Guard(1, 8),
            Guard(2, 12),
            Guard(3, 10)
        ]
        self.load_guard_animations()

        self.create_buttons()

        # System states
        self.camera_disabled = False
        self.camera_disable_time = 0
        self.lights_disabled = False
        self.lights_disable_time = 0

        self.event_timer = 0
        self.current_event = None

        # Initialize background video
        self.init_background()
        
        # messages to show feedback to player
        self.feedback_messages = []

        # UI animation timer used for pulsing effects
        self.ui_time = 0.0

        # particle system
        self.particle_sys = ParticleSystem()

        # Initialize transition system
        self.transition_manager = TransitionManager(WIDTH, HEIGHT, 700)
        self.toasts = []
    
    def _on_state_change(self, target_state: str):
        """
        Called when transition reaches midpoint to change game state.
        Args:
            target_state (str): The state to switch to.
        """
        self.state = target_state
 
    def create_icon(self, color, symbol):
        """
        Create a simple icon surface.
        Args:
            color (Tuple[int,int,int]): Color of the icon.
            symbol (str): Symbol to draw on the icon.
        Returns:
            pygame.Surface: Icon surface.
        """
        icon_size =  24
        surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (icon_size//2, icon_size//2), icon_size//2-2)
        font = pygame.font.Font(None, 20)
        text = font.render(symbol, True, WHITE)
        surf.blit(text, text.get_rect(center=(icon_size//2, icon_size//2)))
        return surf

    def _load_icons(self):
        """
        Load button icons.
        """
        self.icons = {
            'clock': self.create_icon((100, 150, 255), 'T'),
            'radar': self.create_icon((255, 100, 100), 'D'),
            'target': self.create_icon((100, 255, 100), 'O'),
            'camera': self.create_icon((100, 100, 200), 'C'),
            'light': self.create_icon((200, 200, 100), 'L'),
            'distract': self.create_icon((200, 100, 200), 'D'),
            'hack': self.create_icon((100, 200, 100), 'H'),
        }
    
    def load_guard_animations(self):
        """
        Load guard animations.
        """
        base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "sprites"))
        sheet_path = os.path.join(base, "guard_sheet.png")
        try:
            for guard in self.guards:
                guard_set = {}
                animations = [
                    ('idle', {'row': 0, 'start_col': 0, 'num_frames': 4, 'speed': 0.2, 'loop': True}),
                    ('walk', {'row': 1, 'start_col': 0, 'num_frames': 6, 'speed': 0.1, 'loop': True}),
                    ('alert', {'row': 2, 'start_col': 0, 'num_frames': 4, 'speed': 0.15, 'loop': True})
                ]
                
                for name, params in animations:
                    anim = Animation(sheet_path, 32, 48)
                    # params already includes 'loop'; avoid passing it twice
                    anim.add_animation(name, **params)
                    # Ensure the animation object has an active animation set
                    anim.set_animation(name, reset=True)
                    guard_set[name] = anim
                
                guard.animation_set = guard_set
                guard.current_anim_name = 'idle'
        except Exception as e:
            pass
        
        # Randomize guard timings
        for guard in self.guards:
            guard.current_time = random.uniform(0, guard.patrol_time)
    
    def init_background(self):
        """
        Initialize background video.
        """
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
        """
        Update the background video frame.
        Args:
            dt (float): Delta time since last update.
        """
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
        """
        Create action buttons for the game.
        """
        button_y = 450
        button_width = 140
        button_height = 50
        spacing = 160
        start_x = 100

        self.buttons = {
            'camera': Button(start_x, button_y, button_width, button_height, "Disable Cams", DARK_BLUE, BLUE,
                             tooltip="Disable security cameras\nReduces detection by 15%\nCooldown: 7s",
                             icon=self.icons['camera'], hotkey="1"),
            'lights': Button(start_x + spacing, button_y, button_width, button_height, "Cut Lights", DARK_BLUE, BLUE,
                             tooltip="Cut the lights in the area\nReduces detection by 10%\nCooldown: 6s",
                             icon=self.icons['light'], hotkey="2"),
            'distract': Button(start_x + 2 * spacing, button_y, button_width, button_height, "Distraction", DARK_BLUE, BLUE,
                             tooltip="Create a distraction to lure guards away\nReduces detection by 20%\nCooldown: 8s",
                             icon=self.icons['distract'], hotkey="3"),
            'hack': Button(start_x + 3 * spacing, button_y, button_width, button_height, "Hack System", DARK_GREEN, GREEN,
                           tooltip="Hack into the security system\nReduces detection by 25%\nCooldown: 10s",
                           icon=self.icons['hack'], hotkey="4"),
            'menu': Button(WIDTH//2 - 100, HEIGHT//2 + 100, 200, 50, "START MISSION", DARK_GREEN, GREEN)
        }

    def add_toast(self, text: str, color, duration: float = 2.0):
        """
        Add a toast notification.
        Args:
            text (str): The text of the toast.
            color (Tuple[int,int,int]): The color of the toast text.
            duration (float): Duration in seconds the toast should be visible.
        """
        self.toasts.append({
            'text': text,
            'color': color,
            'time': duration,
            'duration': duration,
        })

    def reset_game(self):
        """
        Reset the game state.
        """
        self.time_remaining = self.mission_time
        self.animated_time = self.mission_time
        self.detection_level = 0
        self.animated_detection = 0.0
        self.objective_progress = 0
        self.animated_objectives = 0.0
        self.camera_disabled = False
        self.camera_disable_time = 0
        self.camera_blink_time = 0.0
        self.camera_blink_active = False
        self.lights_disabled = False
        self.lights_disable_time = 0
        self.event_timer = 0
        self.current_event = None

        for guard in self.guards:
            guard.alert = False
            guard.alert_time = 0.0
            guard.current_time = random.uniform(0, guard.patrol_time)
        
        self.create_buttons()
        self.particle_sys.clear()
        self.toasts.clear()
        self.feedback_messages.clear()

    def handle_events(self):
        """
        Handle user input events.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                self._handle_keyboard(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if self.state == "menu":
                    if self.buttons['menu'].is_clicked(pos):
                        self.reset_game()
                        video_path = os.path.join(os.path.dirname(__file__), "..", "assets", "videos", "hacking bg.mp4")
                        self.transition_manager.start_transition(
                            "playing",
                            TransitionType.FADE_VIDEO,
                            speed=500,
                            state_change_callback=self._on_state_change,
                            video_path=video_path,
                            video_speed=3
                        )
                    
                elif self.state == "playing":
                    self._handle_game_clicks(pos)
                
                elif self.state in ["success", "failure"]:
                    if self.buttons['menu'].is_clicked(pos):
                        self.reset_game()
                        self.transition_manager.start_transition(
                            target_state="menu",
                            transition_type=TransitionType.SLIDE_DOWN,
                            speed=600,
                            state_change_callback=self._on_state_change,
                            color=(20, 20, 40)
                        )

    def _handle_keyboard(self, key):
        """
        Handle keyboard shortcuts for buttons.
        Args:
            key (int): The pygame key code.
        """
        if self.state == "playing":
            action_map = {
                pygame.K_1: 'camera',
                pygame.K_2: 'lights',
                pygame.K_3: 'distract',
                pygame.K_4: 'hack',
            }

            button_key = action_map.get(key)
            if button_key and self.buttons[button_key].active:
                self._handle_game_clicks(self.buttons[button_key].rect.center)

    def _handle_game_clicks(self, pos):
        """
        Handle clicks on game action buttons.
        Args:
            pos (Tuple[int, int]): The position of the mouse click.
        """
        if self.buttons['camera'].is_clicked(pos):
            self.buttons['camera'].press()
            self.camera_disabled = True
            self.camera_disable_time = 8
            self.buttons['camera'].set_cooldown(7)
            self.add_toast("Cameras Disabled", BLUE, 2.0)
            self.camera_blink_time = 0.5
            self.camera_blink_active = True
            delta = -15
            self.detection_level = max(0, self.detection_level + delta)
            bx, by = self.buttons['camera'].rect.center
            self.particle_sys.spawn_smoke(bx, by, count=12)
            self.particle_sys.add_detection_popup(delta, bx, by)

        elif self.buttons['lights'].is_clicked(pos):
            self.buttons['lights'].press()
            self.lights_disabled = True
            self.lights_disable_time = 6
            self.buttons['lights'].set_cooldown(5)
            self.add_toast("Lights Cut", BLUE, 2.0)
            delta = -10
            self.detection_level = max(0, self.detection_level + delta)
            lx, ly = self.buttons['lights'].rect.center
            self.particle_sys.spawn_smoke(lx, ly, count=8)
            self.particle_sys.add_detection_popup(delta, lx, ly)
        
        elif self.buttons['distract'].is_clicked(pos):
            self.buttons['distract'].press()
            # Clear all guard alerts
            for guard in self.guards:
                guard.alert = False
            delta = -20
            self.detection_level = max(0, self.detection_level + delta)
            dx, dy = self.buttons['distract'].rect.center
            self.particle_sys.spawn_smoke(dx, dy, count=14)
            self.particle_sys.add_detection_popup(delta, dx, dy)
            self.buttons['distract'].set_cooldown(10)
            self.add_toast("Distraction Created", BLUE, 2.0)
        
        elif self.buttons['hack'].is_clicked(pos):
            self.buttons['hack'].press()
            # Success chance decreases with detection level
            success_chance = max(0.15, 1.0 - (self.detection_level / 80.0))
            if random.random() < success_chance:
                self.objective_progress += 1
                delta = -5
                self.detection_level = max(0, self.detection_level + delta)
                self.buttons['hack'].set_cooldown(2.0)
                self.add_toast(f"HACK SUCCESSFUL! ({self.objective_progress}/{self.objectives_needed})", GREEN, 2.5)
                self.feedback_messages.append({'text': "HACK SUCCESSFUL", 'color': GREEN, 'time': 2.5})
                hx, hy = WIDTH//2, 220
                self.particle_sys.spawn_sparks(hx, hy, count=18, color=(255,220,120))
                self.particle_sys.add_detection_popup(delta, hx, hy)
                self.particle_sys.start_shake(3.0, 0.25)
            else:
                penalty = min(20, int(8 + self.detection_level * 0.05))
                self.detection_level += penalty
                self.buttons['hack'].set_cooldown(3.5)
                self.add_toast(f"HACK FAILED! +{penalty}% detection", RED, 2.5)
                self.feedback_messages.append({'text': "HACK FAILED", 'color': RED, 'time': 2.5})
                hx, hy = WIDTH//2, 220
                self.particle_sys.spawn_sparks(hx, hy, count=26, color=(255,80,60))
                self.particle_sys.add_detection_popup(+penalty, hx, hy)
                self.particle_sys.start_shake(8.0, 0.4)

    def update(self, dt):
        """
        Update the game state.
        Args:
            dt (float): Delta time since last update.
        """
        transition_result = self.transition_manager.update(dt)

        if transition_result['active']:
            return
        
        if self.state != "playing":
            return

        self.time_remaining -= dt
        self.ui_time += dt

        # Smooth interpolation for animated values
        lerp = lambda a, b, t: a + (b - a) * min(1.0, t)
        self.animated_time = lerp(self.animated_time, self.time_remaining, dt * 4.0)
        self.animated_detection = lerp(self.animated_detection, self.detection_level, dt * 4.0)
        self.animated_objectives = lerp(self.animated_objectives, self.objective_progress, dt * 4.0)

        # Camera blink animation
        if self.camera_blink_time > 0:
            self.camera_blink_time -= dt
            if self.camera_blink_time <= 0:
                self.camera_blink_active = False

        for button in self.buttons.values():
            button.update(dt)
        
        if self.camera_disable_time > 0:
            self.camera_disable_time -= dt
            if self.camera_disable_time <= 0:
                self.camera_disabled = False
                self.camera_blink_time = 0.3
                self.camera_blink_active = True
        
        if self.lights_disable_time > 0:
            self.lights_disable_time -= dt
        else:
            self.lights_disabled = False
        
        for guard in self.guards:
            guard.update(dt)
        
        # Base detection increases over time
        base_detection = 2 * dt
        if self.camera_disabled:
            base_detection *= 0.3
        if self.lights_disabled:
            base_detection *= 0.5
        
        self.detection_level += base_detection

        # Guards can spot player in danger zone
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
                    gx = 100 + int(guard.position * 800)
                    gy = 150 + (self.guards.index(guard) * 60) + 20
                    self.particle_sys.spawn_sparks(gx, gy, count=6, color=(255,180,80))
                    self.particle_sys.add_detection_popup(+delta, gx, gy)
        
        self.event_timer += dt
        if self.event_timer >= 5:
            self.event_timer = 0
            self.trigger_random_event()
        
        # handle current event effects
        if isinstance(self.current_event, dict):
            dps = self.current_event.get('dps', 0)
            if dps:
                self.detection_level += dps * dt
            self.current_event['time_left'] -= dt
            if self.current_event['time_left'] <= 0:
                self.current_event = None
        
        self.particle_sys.update(dt)
        
        # Cleanup feedback messages
        for m in list(self.feedback_messages):
            m['time'] -= dt
            if m['time'] <= 0:
                self.feedback_messages.remove(m)

        # Check win/loss conditions
        self.detection_level = max(0, min(self.detection_level, self.max_detection))
        if self.objective_progress >= self.objectives_needed:
            self.state = "success"
            self.particle_sys.clear()
        elif self.detection_level >= self.max_detection or self.time_remaining <= 0:
            self.state = "failure"
            self.particle_sys.clear()
        
        # Update toasts
        for toast in list(self.toasts):
            toast['time'] -= dt
            if toast['time'] <= 0:
                self.toasts.remove(toast)
            else:
                alpha_ratio = toast['time'] / toast['duration']
                toast['alpha'] = int(255 * min(1.0, alpha_ratio * 2.0))
        
    def trigger_random_event(self):
        """
        Trigger a random security event.
        """
        events = [
            {'text': "Security sweep initiated", 'duration': 6.0, 'instant': random.randint(5, 12), 'dps': 1.0},
            {'text': "Guard shift change", 'duration': 8.0, 'instant': 0, 'dps': 0.5},
            {'text': "System scan detected", 'duration': 5.0, 'instant': random.randint(8, 16), 'dps': 1.5},
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
        if inst >= 10:
            self.particle_sys.start_shake(9.0, 0.5)
    
    def draw(self):
        """
        Draw the current game state.
        """
        # render everything to a temp canvas so we can blit with screen shake offset
        self.canvas.fill((0,0,0))
        old_screen = self.screen
        self.screen = self.canvas

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
        self.screen.blit(self.canvas, (ox, oy))

        self.transition_manager.draw(self.screen)

        pygame.display.flip()
    
    def draw_menu(self):
        """
        Draw the main menu.
        """
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
        """
        Draw the main game UI.
        """
        title = self.title_font.render("SECURITY TERMINAL", True, GREEN)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))

        self.draw_status_bars(25, 90, 300, 30, "TIME", self.animated_time, self.mission_time, BLUE, self.icons['clock'])
        self.draw_status_bars(WIDTH - 325, 90, 300, 30, "DETECTION", self.animated_detection, self.max_detection, RED, self.icons['radar'])
        self.draw_mission_progress(WIDTH//2 - 150, 90, 300, 30)

        # Show feedback messages
        for i, msg in enumerate(self.feedback_messages):
            txt = self.font.render(msg['text'], True, msg['color'])
            txt_rect = txt.get_rect(center=(WIDTH//2, 130 + i * 30))
            self.screen.blit(txt, txt_rect)

        # Draw guard monitors
        monitor_y = 150
        for i, guard in enumerate(self.guards):
            guard.draw(self.screen, 100, monitor_y + i * 60, 800, 40)

        # System statuses
        status_y = 350
        systems = [
            ("CAMERAS", "OFFLINE" if self.camera_disabled else "ONLINE", 
             GREEN if self.camera_disabled else RED, self.camera_blink_active),
            ("LIGHTS", "OFFLINE" if self.lights_disabled else "ONLINE", GREEN if self.lights_disabled else RED)
        ]

        for i, sys_data in enumerate(systems):
            name = sys_data[0]
            status = sys_data[1]
            color = sys_data[2]
            blink = sys_data[3] if len(sys_data) > 3 else False
            if blink and int(self.ui_time *  10) % 2 == 0:
                color = YELLOW
            text = self.small_font.render(f"{name}: {status}", True, color)
            self.screen.blit(text, (100 + i * 250, status_y))

        # Show current event
        if self.current_event:
            ev_text = self.current_event['text'] if isinstance(self.current_event, dict) else str(self.current_event)
            event_text = self.small_font.render(f"! {ev_text}", True, YELLOW)
            self.screen.blit(event_text, (WIDTH//2 - event_text.get_width()//2, 390))

        for key in ['camera', 'lights', 'distract', 'hack']:
            show_tooltip = self.buttons[key].is_hovered()
            self.buttons[key].draw(self.screen, self.small_font, show_tooltip)

        self.draw_toasts()

    def draw_status_bars(self, x, y, width, height, label, value, max_value, color, icon=None):
        """
        Draw a status bar with label, value, and icon.
        Args:
            x (int): X position.
            y (int): Y position.
            width (int): Width of the bar.
            height (int): Height of the bar.
            label (str): Label text.
            value (float): Current value.
            max_value (float): Maximum value.
            color (Tuple[int,int,int]): Color of the filled portion.
            icon (pygame.Surface): Optional icon to display.
        """
        label_text = self.small_font.render(label, True, WHITE)
        self.screen.blit(label_text, (x, y - 25))

        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, width, height))

        if max_value > 0:
            fill_width = int((value / max_value) * width)
            fill_width = max(0, min(fill_width, width))
        
            # pulsing effect for detection bar when high
            draw_color = color
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

        # Border
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        # Icon
        if icon:
            icon_x = x + 5
            icon_y = y + height//2 - icon.get_height()//2
            self.screen.blit(icon, (icon_x, icon_y))

        if label == 'TIME':
            value_text = self.small_font.render(f"{int(value)}s", True, WHITE)
        else:
            value_text = self.small_font.render(f"{int(value)}%", True, WHITE)
        
        text_rect = value_text.get_rect(center=(x + width//2, y + height//2))
        self.screen.blit(value_text, text_rect)

    def draw_mission_progress(self, x, y, width, height):
        """
        Draw the mission progress bar.
        Args:
            x (int): X position.
            y (int): Y position.
            width (int): Width of the bar.
            height (int): Height of the bar.
        """
        # Label
        label = self.small_font.render("MISSION", True, WHITE)
        self.screen.blit(label, (x, y - 25))

        # Progress
        progress = self.animated_objectives / self.objectives_needed

        # Background
        pygame.draw.rect(self.screen, DARK_GRAY, (x, y, width, height))

        # Fill
        fill_width = int(progress * width)
        gradient_color = (
            int(255 * (1 - progress) + 0 * progress),
            int(0 * (1 - progress) + 255 * progress),
            0
        )
        pygame.draw.rect(self.screen, gradient_color, (x, y, fill_width, height))

        # Border
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)

        # Icon
        icon = self.icons['target']
        icon_x = x + 5
        icon_y = y + height//2 - icon.get_height()//2
        self.screen.blit(icon, (icon_x, icon_y))

        # Percentage
        percentage = int(progress * 100)
        progress_text = self.font.render(f"{percentage}%", True, WHITE)
        text_rect = progress_text.get_rect(center=(x + width//2, y + height//2))
        self.screen.blit(progress_text, text_rect)

    def draw_toasts(self):
        """
        Draw toast notifications.
        """
        toast_x = WIDTH // 2
        toast_y = HEIGHT - 100

        for i, toast in enumerate(self.toasts):
            # Slide up animation
            target_y = toast_y - i * 40

            # Redner text
            text_surf = self.font.render(toast['text'], True, toast['color'])
            text_surf.set_alpha(toast.get('alpha', 255))

            # Background
            padding = 10
            bg_rect = pygame.Rect(
                toast_x - text_surf.get_width() // 2 - padding,
                target_y - padding,
                text_surf.get_width() + 2 * padding,
                text_surf.get_height() + 2 * padding
            )

            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 180))
            self.screen.blit(bg_surf, bg_rect.topleft)
            pygame.draw.rect(self.screen, toast['color'], bg_rect, 2, border_radius=5)

            # Text
            text_rect = text_surf.get_rect(center=(toast_x, target_y + text_surf.get_height() // 2))
            self.screen.blit(text_surf, text_rect)

    def draw_end_screen(self, message, color):
        """
        Draw the end screen (success or failure).
        Args:
            message (str): The main message to display.
            color (Tuple[int,int,int]): The color of the message text.
        """
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
        """
        Run the main game loop.
        """
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self.update_background(dt)

            self.handle_events()
            self.update(dt)
            self.draw()
        
        self.transition_manager.clear()
        
        if self.bg_cap:
            try:
                self.bg_cap.release()
            except Exception:
                pass
        
        pygame.quit()

if __name__ == "__main__":
    game = StealthGame()
    game.run()