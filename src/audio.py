import pygame
import os
import json
import numpy as np
from typing import Dict, Optional

class AudioManager:
    def __init__(self):
        """Initialize the audio manager."""
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.audio_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "audio"))

        # Volume settings
        self.master_volume = 0.7
        self.music_volume = 0.5
        self.sfx_volume = 0.8

        # Audio channels
        self.sfx_channels = [pygame.mixer.Channel(i) for i in range(8)]
        self.current_channel = 0
        self.sfx_sounds = {}

        self.settings_file = os.path.join(os.path.dirname(__file__), "audio_settings.json")
        self.load_settings()
        self.load_sounds()
    
    def load_settings(self):
        """Load audio settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.master_volume = settings.get("master_volume", 0.7)
                    self.music_volume = settings.get("music_volume", 0.5)
                    self.sfx_volume = settings.get("sfx_volume", 0.8)
        except Exception as e:
            print(f"Error loading audio settings: {e}")
        
    def save_settings(self):
        """Save audio settings to file."""
        try:
            settings = {
                "master_volume": self.master_volume,
                "music_volume": self.music_volume,
                "sfx_volume": self.sfx_volume
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving audio settings: {e}")

    def _generate_tone(self, frequency, duration, volume=0.5):
        """Generate a simple tone sound."""
        sample_rate = 44100
        frames = int(sample_rate * duration)
        arr = np.zeros((frames, 2))

        for i in range(frames):
            t = i / sample_rate
            wave = np.sin(2 * np.pi * frequency * t) * volume
            if i < 1000:
                wave *= i / 1000
            elif i > frames - 1000:
                wave *= (frames - i) / 1000
            arr[i] = [wave, wave]
        
        arr = (arr * 32767).astype(np.int16)
        return pygame.mixer.Sound(arr)

    def load_sounds(self):
        """Load sound effects from the audio directory."""
        sfx_dir = os.path.join(self.audio_dir, "sfx")

        # Generate sounds
        sounds = {
             'button_click': (800, 0.1, 0.3),
             'button_hover': (600, 0.05, 0.2),
             'alert_beep': (1000, 0.2, 0.4),
             'footsteps': (200, 0.1, 0.3),
             'hack_success': (523, 0.3, 0.5),
             'hack_fail': (200, 0.4, 0.4),
             'camera_disable': (800, 0.3, 0.4),
             'lights_cut': (400, 0.2, 0.3),
             'distraction': (440, 0.2, 0.4),
             'system_startup': (400, 0.5, 0.3),
             'countdown_tick': (1200, 0.05, 0.3),
             'mission_complete': (659, 0.8, 0.6),
             'mission_failed': (150, 1.0, 0.5)
         }

        for name, (freq, dur, vol) in sounds.items():
            for ext in ['.wav', '.ogg', '.mp3']:
                file_path = os.path.join(sfx_dir, f"{name}{ext}")
                if os.path.exists(file_path):
                    try:
                        self.sfx_sounds[name] = pygame.mixer.Sound(file_path)
                        break
                    except Exception as e:
                        print(f"Error loading sound {name}: {e}")
                        continue
            else:
                self.sfx_sounds[name] = self._generate_tone(freq, dur, vol)

    def play_sfx(self, sound_name, volume_override=None):
        """Play a sound effect"""
        if sound_name not in self.sfx_sounds:
            print(f"Sound {sound_name} not found!")
            return
        
        channel = None
        for ch in self.sfx_channels:
            if not ch.get_busy():
                channel = ch
                break
        
        if not channel:
            channel = self.sfx_channels[self.current_channel]
            self.current_channel = (self.current_channel + 1) % len(self.sfx_channels)
        
        volume = (volume_override or 1.0) * self.sfx_volume * self.master_volume
        channel.set_volume(volume)
        channel.play(self.sfx_sounds[sound_name])
    
    def play_music(self, music_name, loop=True, fade_in=0):
        """Play background music."""
        music_dir = os.path.join(self.audio_dir, "music")

        for ext in ['.mp3', '.ogg', '.wav']:
            music_path = os.path.join(music_dir, f"{music_name}{ext}")
            if os.path.exists(music_path):
                try:
                    pygame.mixer.music.load(music_path)
                    if fade_in > 0:
                        pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_in*1000)
                    else:
                        pygame.mixer.music.play(-1 if loop else 0)
                    pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
                    return
                except Exception as e:
                    print(f"Error loading music {music_name}: {e}")
                    continue
    
    def stop_music(self, fade_out: float = 0):
        """Stop background music."""
        if fade_out > 0:
            pygame.mixer.music.fadeout(int(fade_out * 1000))
        else:
            pygame.mixer.music.stop()
    
    def duck_music(self, duck_volume: float = 0.3):
        """Lower music volume temporarily."""
        pygame.mixer.music.set_volume(duck_volume * self.master_volume)
    
    def unduck_music(self):
        """Restore music volume."""
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
    
    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume * self.master_volume)
        self.save_settings()
    
    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        self.save_settings()
    
    def get_volumes(self) -> Dict[str, float]:
        return {'master': self.master_volume, 'music': self.music_volume, 'sfx': self.sfx_volume}
    
    def is_music_playing(self) -> bool:
        return pygame.mixer.music.get_busy()