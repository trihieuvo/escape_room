# player.py
import pygame
import os
import sys
import math
from constants import (
    CELL_SIZE, PLAYER_MOVE_SPEED, PLAYER_ANIMATION_SPEED,
    FALLBACK_IMAGE_COLOR, IMAGE_FOLDER,
    PLAYER_IDLE_IMAGE, PLAYER_WIN_IMAGE, PLAYER_WALK_PREFIX,
    KEY_PICKUP_SOUND, PLAYER_MUD_MULTIPLIER,
    DMG_PRIMARY_GREEN, DMG_DARK_BG, DMG_LIGHT_TEXT, # Theme colors
    DMG_ACCENT_GREEN
)
from utils import load_scaled_image, load_sound
from maze import Maze

class Player:
    def __init__(self, start_x: int, start_y: int, cell_size: int, game_speed_ref: list[float]):
        self.x = start_x
        self.y = start_y
        self.cell_size = cell_size
        self.game_speed_ref = game_speed_ref
        self._load_sprites()
        self.direction = 'right'
        self.is_moving = False
        self.animation_timer = 0.0
        self.move_timer = 0.0
        self.current_frame_index = 0
        self.keys_collected = 0
        self.just_slid = False
        self.just_teleported = False
        self.move_count = 0
        self.key_pickup_sound = load_sound(KEY_PICKUP_SOUND)
        self.current_image = self.idle_img_right

    def _load_sprites(self):
        self.idle_img_right = load_scaled_image(PLAYER_IDLE_IMAGE, self.cell_size)
        if self.idle_img_right.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR) and not os.path.exists(os.path.join(IMAGE_FOLDER,PLAYER_IDLE_IMAGE)):
            print(f"W: Player idle image '{PLAYER_IDLE_IMAGE}' not found. Using fallback.", file=sys.stderr)
            self.idle_img_right = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.idle_img_right.fill(DMG_ACCENT_GREEN)
            pygame.draw.circle(self.idle_img_right, DMG_LIGHT_TEXT, (self.cell_size//2, self.cell_size//2), self.cell_size//3)
        self.idle_img_left = pygame.transform.flip(self.idle_img_right, True, False)


        self.walk_frames_right = []
        MAX_PLAYER_WALK_FRAMES = 8 
        for i in range(MAX_PLAYER_WALK_FRAMES):
            filename = f"{PLAYER_WALK_PREFIX}{i}.png"
            image_path = os.path.join(IMAGE_FOLDER, filename)

            if not os.path.exists(image_path): 
                if i == 0: 
                    print(f"W: Player walk frame '{filename}' (start of sequence) not found. Walk animation may be missing.", file=sys.stderr)
                break 
            frame = load_scaled_image(filename, self.cell_size)

            if frame.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR):
                print(f"W: Error loading player walk frame '{filename}' (file exists but failed to load). Stopping sequence.", file=sys.stderr)
                break 

            self.walk_frames_right.append(frame)



        if not self.walk_frames_right:
            print(f"W: No player walk frames loaded. Using idle image for walking animation.", file=sys.stderr)
            self.walk_frames_right.append(self.idle_img_right)
        self.walk_frames_left = [pygame.transform.flip(img, True, False) for img in self.walk_frames_right]


        win_size = int(self.cell_size * 2.2)
        self.win_image = load_scaled_image(PLAYER_WIN_IMAGE, win_size)
        if self.win_image.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR):
            print(f"W: Player win image '{PLAYER_WIN_IMAGE}' not found or failed to load. Using fallback.", file=sys.stderr)
            self.win_image = pygame.Surface((win_size, win_size), pygame.SRCALPHA)
            center_x, center_y = win_size // 2, win_size // 2
            base_color = DMG_PRIMARY_GREEN
            highlight_color = DMG_ACCENT_GREEN
            pygame.draw.rect(self.win_image, base_color, (center_x - win_size//6, center_y + win_size//8, win_size//3, win_size//4), border_radius=4)
            pygame.draw.rect(self.win_image, base_color, (center_x - win_size//12, center_y - win_size//8, win_size//6, win_size//4))
            pygame.draw.ellipse(self.win_image, highlight_color, (center_x - win_size//3, center_y - win_size//2, win_size*2//3, win_size//2.5))
            pygame.draw.ellipse(self.win_image, DMG_DARK_BG, (center_x - win_size//3 + 3, center_y - win_size//2 + 3, win_size*2//3 -6, win_size//2.5-6))
            pygame.draw.arc(self.win_image, highlight_color, (center_x - win_size//2.5, center_y - win_size//2.5, win_size//3, win_size//2), -math.pi/2, math.pi/2, 4)
            pygame.draw.arc(self.win_image, highlight_color, (center_x + win_size//2.5 - win_size//3, center_y - win_size//2.5, win_size//3, win_size//2), math.pi/2, 3*math.pi/2, 4)


    def handle_input(self, keys: pygame.key.ScancodeWrapper, maze: Maze, dt: float):
        effective_dt = dt * self.game_speed_ref[0]
        effective_player_move_speed = PLAYER_MOVE_SPEED / self.game_speed_ref[0]

        self.move_timer += effective_dt
        moved_this_grid_cell = False

        player_is_pressing_move_key = any(keys[k] for k in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s])
        if self.just_slid and not player_is_pressing_move_key: self.just_slid = False
        if self.just_teleported and not player_is_pressing_move_key: self.just_teleported = False

        dx, dy = 0, 0
        current_facing_direction = self.direction

        current_move_delay = effective_player_move_speed
        if maze.is_mud(self.x, self.y):
            current_move_delay *= PLAYER_MUD_MULTIPLIER

        if not self.just_slid and not self.just_teleported and self.move_timer >= current_move_delay:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx = -1; current_facing_direction = 'left'
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx = 1; current_facing_direction = 'right'
            elif keys[pygame.K_UP] or keys[pygame.K_w]: dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]: dy = 1

            self.direction = current_facing_direction

            if dx != 0 or dy != 0:
                next_x, next_y = self.x + dx, self.y + dy

                if maze.is_water(next_x, next_y):
                    entry_dx, entry_dy = dx, dy
                    sim_curr_x, sim_curr_y = next_x, next_y
                    while True:
                        look_ahead_x = sim_curr_x + entry_dx
                        look_ahead_y = sim_curr_y + entry_dy
                        if maze.is_wall(look_ahead_x, look_ahead_y):
                            final_x, final_y = sim_curr_x, sim_curr_y; break
                        elif not maze.is_water(look_ahead_x, look_ahead_y):
                            final_x, final_y = look_ahead_x, look_ahead_y; break
                        else:
                            sim_curr_x, sim_curr_y = look_ahead_x, look_ahead_y

                    if maze.is_portal(final_x, final_y):
                        target_portal = maze.get_portal_target(final_x, final_y)
                        if target_portal: self.x, self.y = target_portal; self.just_teleported = True
                        else: self.x, self.y = final_x, final_y
                    else: self.x, self.y = final_x, final_y
                    self.just_slid = True; moved_this_grid_cell = True

                elif maze.is_portal(next_x, next_y):
                    target_portal = maze.get_portal_target(next_x, next_y)
                    if target_portal:
                        self.x, self.y = target_portal
                        self.just_teleported = True; moved_this_grid_cell = True
                    elif not maze.is_wall(next_x, next_y):
                        self.x, self.y = next_x, next_y; moved_this_grid_cell = True

                elif not maze.is_wall(next_x, next_y):
                    self.x, self.y = next_x, next_y
                    moved_this_grid_cell = True

                if moved_this_grid_cell:
                    self.move_timer = 0.0
                    self.move_count += 1
                    self.is_moving = True
                    if self.just_slid and (dx != 0 or dy !=0): self.just_slid = False
                    if self.just_teleported and (dx != 0 or dy !=0): self.just_teleported = False
                else:
                    self.is_moving = False
            else:
                self.is_moving = False

        if (self.just_slid or self.just_teleported) and not player_is_pressing_move_key:
            self.is_moving = False


    def update_animation(self, dt: float):
        effective_dt = dt * self.game_speed_ref[0]
        effective_player_animation_speed = PLAYER_ANIMATION_SPEED / self.game_speed_ref[0]

        self.animation_timer += effective_dt
        if self.animation_timer >= effective_player_animation_speed:
            self.animation_timer %= effective_player_animation_speed 
            if self.is_moving:
                walk_frames = self.walk_frames_right if self.direction == 'right' else self.walk_frames_left
                if walk_frames:
                    self.current_frame_index = (self.current_frame_index + 1) % len(walk_frames)
            else: # Not moving
                self.current_frame_index = 0

        if not self.is_moving:
            self.current_image = self.idle_img_right if self.direction == 'right' else self.idle_img_left
        elif self.is_moving and self.walk_frames_right: 
             walk_frames_current_dir = self.walk_frames_right if self.direction == 'right' else self.walk_frames_left
             if walk_frames_current_dir: 
                idx_to_use = self.current_frame_index % len(walk_frames_current_dir)
                self.current_image = walk_frames_current_dir[idx_to_use]
             else: 
                self.current_image = self.idle_img_right if self.direction == 'right' else self.idle_img_left


    def update(self, keys: pygame.key.ScancodeWrapper, maze: Maze, dt: float):
        self.handle_input(keys, maze, dt)

        can_pickup_key = not self.just_slid and not self.just_teleported

        if can_pickup_key and maze.is_key(self.x, self.y):
            if maze.remove_key(self.x, self.y):
                self.collect_key()

        self.update_animation(dt)

    def draw(self, surface: pygame.Surface):
        draw_x = self.x * self.cell_size
        draw_y = self.y * self.cell_size
        surface.blit(self.current_image, (draw_x, draw_y))

    def get_pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def collect_key(self):
        self.keys_collected += 1
        if self.key_pickup_sound:
            self.key_pickup_sound.play()

    def get_keys_collected(self) -> int:
        return self.keys_collected

    def reset_state(self):
        self.keys_collected = 0
        self.just_slid = False
        self.just_teleported = False
        self.is_moving = False
        self.move_timer = 0.0
        self.animation_timer = 0.0
        self.current_frame_index = 0
        self.move_count = 0
        if hasattr(self, 'idle_img_right'):
            self.current_image = self.idle_img_right
        self.direction = 'right'