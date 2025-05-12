import pygame
import random
import os
import sys
from constants import (
    WALL_COLOR, PATH_COLOR, EXIT_COLOR, KEY_COLOR, MUD_COLOR, WATER_COLOR, PORTAL_COLORS_FALLBACK,
    CELL_SIZE, FALLBACK_IMAGE_COLOR, IMAGE_FOLDER, 
    EXIT_IMAGE_FILENAME, KEY_IMAGE_FILENAME, MUD_IMAGE_FILENAME, WATER_IMAGE_FILENAME,
    PATH_IMAGE_FILENAME, PORTAL_IMAGE_PREFIX,
    MIN_SLIDE_LENGTH, MAX_SLIDE_LENGTH, MAX_PORTAL_PAIRS,
    MUD_COST_ALGO, PORTAL_COST_ALGO, SLIDE_CELL_COST_ALGO,
    PORTAL_ANIMATION_SPEED, MAX_PORTAL_ANIMATION_FRAMES,
    DMG_PRIMARY_GREEN, DMG_DARK_BG, DMG_ACCENT_GREEN # Theme colors for fallbacks
)
from utils import load_scaled_image

class Maze:
    def __init__(self, width, height, cell_size, num_keys, num_puddles, num_slides, num_portal_pairs, loop_chance=0.1):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.loop_chance = loop_chance
        self.num_keys_target = num_keys
        self.num_puddles_target = num_puddles
        self.num_slides_target = num_slides
        self.num_portal_pairs_target = min(num_portal_pairs, MAX_PORTAL_PAIRS if MAX_PORTAL_PAIRS >=0 else 0)

        self.start_pos = (1, 1)
        exit_x = width - 2 if width > 1 else 1
        exit_y = height - 2 if height > 1 else 1
        self.exit_pos = (max(1, exit_x), max(1, exit_y))
        if self.start_pos == self.exit_pos and (width > 3 or height > 3): # Try to move exit if same as start
            self.exit_pos = (max(1, exit_x - 2 if exit_x - 2 > 0 else exit_x + (0 if exit_x > 1 else 1)), self.exit_pos[1])
            if self.start_pos == self.exit_pos: # Still same? Try moving Y
                 self.exit_pos = (self.exit_pos[0], max(1, exit_y - 2 if exit_y - 2 > 0 else exit_y + (0 if exit_y > 1 else 1)))

        self.maze_data = self._generate_maze()

        self.keys = []
        self.mud_puddles = set()
        self.water_cells = set()
        self.portals = {} 
        self.portal_locations = set()

        self.portal_pair_frames = {} 
        self.portal_pair_use_texture = {} 
        self.portal_animation_timer = 0.0
        self.portal_current_frame_index = 0
        self.min_loaded_portal_frames = 0 

        self.MUD_COST_FOR_ALGORITHM = MUD_COST_ALGO
        self.PORTAL_COST_FOR_ALGORITHM = PORTAL_COST_ALGO
        self.SLIDE_CELL_COST_FOR_ALGORITHM = SLIDE_CELL_COST_ALGO

        self.actual_num_slides = self._place_slides(self.num_slides_target)
        self.actual_num_portal_pairs = self._place_portals(self.num_portal_pairs_target)
        self._load_portal_animations() 
        self.actual_num_keys = self._place_keys(self.num_keys_target)
        self.actual_num_puddles = self._place_puddles(self.num_puddles_target)

        # Load images (or their fallbacks)
        self.exit_img = load_scaled_image(EXIT_IMAGE_FILENAME, self.cell_size)
        self.key_img = load_scaled_image(KEY_IMAGE_FILENAME, int(self.cell_size * 0.85)) 
        self.mud_img = load_scaled_image(MUD_IMAGE_FILENAME, self.cell_size)
        self.water_img = load_scaled_image(WATER_IMAGE_FILENAME, self.cell_size)
        self.path_img = load_scaled_image(PATH_IMAGE_FILENAME, self.cell_size)

        # Flags to determine if actual textures should be used or fallbacks
        self.use_exit_texture = self.exit_img.get_at((0,0)) != pygame.Color(FALLBACK_IMAGE_COLOR)
        self.use_key_texture = self.key_img.get_at((0,0)) != pygame.Color(FALLBACK_IMAGE_COLOR)
        self.use_mud_texture = self.mud_img.get_at((0,0)) != pygame.Color(FALLBACK_IMAGE_COLOR)
        self.use_water_texture = self.water_img.get_at((0,0)) != pygame.Color(FALLBACK_IMAGE_COLOR)
        
        # Path texture usage check (more robust)
        is_path_fallback = self.path_img.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR)
        path_file_exists = os.path.exists(os.path.join(IMAGE_FOLDER, PATH_IMAGE_FILENAME))
        if is_path_fallback and not path_file_exists: # File genuinely missing
            self.use_path_texture = False
        elif is_path_fallback and path_file_exists: # File exists but loaded as fallback (error)
            print(f"W: Path texture '{PATH_IMAGE_FILENAME}' loaded as fallback (load error), disabling texture.", file=sys.stderr)
            self.use_path_texture = False
        else: # Loaded successfully
            self.use_path_texture = True


    def _generate_maze(self):
        maze = [[1 for _ in range(self.width)] for _ in range(self.height)]
        if self.width <= 2 or self.height <= 2: return maze # Basic border for tiny mazes
        
        def is_valid_carve_pos(x, y): # Check if within inner maze boundaries for carving
            return 1 <= x < self.width - 1 and 1 <= y < self.height - 1

        def carve(x, y):
            maze[y][x] = 0 # Carve path
            directions = [(0, 2), (2, 0), (0, -2), (-2, 0)] # N, E, S, W (jumping 2 cells)
            random.shuffle(directions)
            for dx, dy in directions:
                next_x, next_y = x + dx, y + dy
                if is_valid_carve_pos(next_x, next_y) and maze[next_y][next_x] == 1: # If next cell is wall
                    maze[y + dy // 2][x + dx // 2] = 0 # Carve wall in between
                    carve(next_x, next_y)
        
        carve(self.start_pos[0], self.start_pos[1]) # Start carving from start_pos

        # Add loops based on loop_chance
        for y_loop in range(1, self.height - 1, 2): # Iterate over potential path cells
            for x_loop in range(1, self.width - 1, 2):
                if maze[y_loop][x_loop] == 0 and random.random() < self.loop_chance: # If it's a path and chance met
                    potential_walls_to_break = []
                    # Check adjacent walls that could be broken to form a loop with another path cell
                    # Check North wall (if it leads to another path cell)
                    if y_loop > 1 and maze[y_loop - 1][x_loop] == 1 and y_loop - 2 > 0 and maze[y_loop-2][x_loop] == 0:
                        potential_walls_to_break.append((x_loop, y_loop - 1))
                    # Check South wall
                    if y_loop < self.height - 2 and maze[y_loop + 1][x_loop] == 1 and y_loop + 2 < self.height -1 and maze[y_loop+2][x_loop] == 0:
                        potential_walls_to_break.append((x_loop, y_loop + 1))
                    # Check West wall
                    if x_loop > 1 and maze[y_loop][x_loop - 1] == 1 and x_loop - 2 > 0 and maze[y_loop][x_loop-2] == 0:
                        potential_walls_to_break.append((x_loop - 1, y_loop))
                    # Check East wall
                    if x_loop < self.width - 2 and maze[y_loop][x_loop + 1] == 1 and x_loop + 2 < self.width -1 and maze[y_loop][x_loop+2] == 0:
                        potential_walls_to_break.append((x_loop + 1, y_loop))
                    
                    if potential_walls_to_break:
                        wall_x, wall_y = random.choice(potential_walls_to_break)
                        maze[wall_y][wall_x] = 0 # Break the wall to create a loop
        
        # Ensure exit is a path cell (it might be a wall if not carved to)
        if 0 <= self.exit_pos[1] < self.height and 0 <= self.exit_pos[0] < self.width:
            maze[self.exit_pos[1]][self.exit_pos[0]] = 0 

        # Ensure exit is accessible from at least one adjacent path cell
        ex, ey = self.exit_pos
        can_reach_exit = False; open_candidates = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]: # Check N, S, W, E neighbors
            nx, ny = ex + dx, ey + dy
            if is_valid_carve_pos(nx,ny): # Check if neighbor is within valid carving area
                if maze[ny][nx] == 0: can_reach_exit = True; break # Already connected
                elif maze[ny][nx] == 1 : open_candidates.append((nx, ny)) # Potential wall to open
        
        if not can_reach_exit and open_candidates: # If exit is walled off, open one wall
            open_x, open_y = random.choice(open_candidates)
            maze[open_y][open_x] = 0
        elif not can_reach_exit and not open_candidates:
             # This is an edge case: exit is on border and surrounded by border, or maze is too small.
             # Might happen if exit_pos is (0,y), (x,0) etc. and maze generation didn't reach it.
             # For now, accept it; pathfinders should fail gracefully.
            # print(f"W: Exit at {self.exit_pos} might be completely inaccessible.", file=sys.stderr)
            pass
        return maze

    def _get_valid_placement_spots(self, exclude_additional=None):
        spots = []
        excluded = {self.start_pos, self.exit_pos}
        if exclude_additional:
            for item_set in exclude_additional: # exclude_additional is a list of sets
                excluded.update(item_set)

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                pos = (x, y)
                if self.maze_data[y][x] == 0 and pos not in excluded:
                    spots.append(pos)
        random.shuffle(spots) # Shuffle to make placement more random
        return spots

    def _place_slides(self, target_num):
        placed_count = 0; attempts = 0; max_attempts = 50 * target_num + 30
        while placed_count < target_num and attempts < max_attempts:
            attempts += 1
            valid_starts = self._get_valid_placement_spots(exclude_additional=[self.water_cells, self.portal_locations])
            if not valid_starts: break

            start_x, start_y = random.choice(valid_starts)
            direction = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            length = random.randint(MIN_SLIDE_LENGTH, MAX_SLIDE_LENGTH)
            
            current_slide_cells = []
            possible = True
            for i in range(length):
                cx, cy = start_x + direction[0]*i, start_y + direction[1]*i
                pos = (cx,cy)
                if not (1 <= cx < self.width-1 and 1 <= cy < self.height-1) or \
                   self.maze_data[cy][cx] == 1 or \
                   pos in self.water_cells or \
                   pos in self.portal_locations or \
                   pos == self.start_pos or pos == self.exit_pos: # Avoid start/exit for slides
                    possible = False; break
                current_slide_cells.append(pos)
            
            if possible and len(current_slide_cells) >= MIN_SLIDE_LENGTH:
                self.water_cells.update(current_slide_cells)
                placed_count += 1
        return placed_count

    def _place_portals(self, target_num_pairs):
        placed_pairs = 0
        target_num_pairs = min(target_num_pairs, len(PORTAL_COLORS_FALLBACK))

        for pair_id in range(target_num_pairs):
            for _ in range(30): # More attempts to find pairs
                valid_spots = self._get_valid_placement_spots(exclude_additional=[self.water_cells, self.portal_locations])
                if len(valid_spots) < 2: break 

                pos1, pos2 = random.sample(valid_spots, 2)
                
                # Ensure portals are not too close (e.g., Manhattan distance > 2)
                if abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]) > 2 :
                    portal_data = {
                        'pair_id': pair_id,
                        'color': PORTAL_COLORS_FALLBACK[pair_id % len(PORTAL_COLORS_FALLBACK)]
                    }
                    self.portals[pos1] = {**portal_data, 'target': pos2}
                    self.portals[pos2] = {**portal_data, 'target': pos1}
                    self.portal_locations.add(pos1)
                    self.portal_locations.add(pos2)
                    placed_pairs += 1
                    break 
            else: 
                # print(f"W: Could not place portal pair {pair_id+1} after several attempts.", file=sys.stderr)
                pass
        return placed_pairs

    def _load_portal_animations(self):
        if self.actual_num_portal_pairs == 0:
            self.min_loaded_portal_frames = 0
            return

        min_frames_for_any_animated_pair = MAX_PORTAL_ANIMATION_FRAMES 

        for pair_id in range(self.actual_num_portal_pairs):
            frames = []
            use_texture_for_this_pair = True 
            for frame_idx in range(MAX_PORTAL_ANIMATION_FRAMES):
                filename = f"{PORTAL_IMAGE_PREFIX}{pair_id}_{frame_idx}.png"
                image_path_check = os.path.join(IMAGE_FOLDER, filename)
                
                img = load_scaled_image(filename, self.cell_size)
                is_fallback = img.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR)
                
                if is_fallback and not os.path.exists(image_path_check):
                    if frame_idx == 0: use_texture_for_this_pair = False # Missing first frame, fallback for pair
                    # print(f"I: Portal anim '{filename}' not found. Sequence for pair {pair_id} may be shorter or fallback.", file=sys.stderr)
                    break 
                elif is_fallback and os.path.exists(image_path_check):
                    print(f"W: Portal animation frame '{filename}' failed to load (file exists). Falling back to color for pair {pair_id}.", file=sys.stderr)
                    use_texture_for_this_pair = False
                    frames.clear(); break
                frames.append(img)

            self.portal_pair_frames[pair_id] = frames
            self.portal_pair_use_texture[pair_id] = use_texture_for_this_pair and bool(frames)

            if use_texture_for_this_pair and frames:
                min_frames_for_any_animated_pair = min(min_frames_for_any_animated_pair, len(frames))
            elif not frames : self.portal_pair_use_texture[pair_id] = False

        if all(not self.portal_pair_use_texture.get(pid, False) for pid in range(self.actual_num_portal_pairs)):
             self.min_loaded_portal_frames = 0
        elif self.actual_num_portal_pairs > 0 :
            valid_frame_counts = [len(self.portal_pair_frames[pid]) 
                                  for pid in range(self.actual_num_portal_pairs) 
                                  if self.portal_pair_use_texture.get(pid) and self.portal_pair_frames.get(pid)]
            if valid_frame_counts: self.min_loaded_portal_frames = min(valid_frame_counts)
            else: self.min_loaded_portal_frames = 0
        else: self.min_loaded_portal_frames = 0


    def _place_keys(self, target_num):
        valid_spots = self._get_valid_placement_spots(exclude_additional=[self.water_cells, self.portal_locations])
        num_to_place = min(target_num, len(valid_spots))
        if num_to_place > 0: self.keys = random.sample(valid_spots, num_to_place)
        else: self.keys = []
        return len(self.keys)

    def _place_puddles(self, target_num):
        valid_spots = self._get_valid_placement_spots(exclude_additional=[set(self.keys), self.water_cells, self.portal_locations])
        num_to_place = min(target_num, len(valid_spots))
        if num_to_place > 0: self.mud_puddles = set(random.sample(valid_spots, num_to_place))
        else: self.mud_puddles = set()
        return len(self.mud_puddles)

    def is_wall(self, x, y):
        return not (0 <= x < self.width and 0 <= y < self.height) or self.maze_data[y][x] == 1
    
    def is_key(self, x, y): return (x,y) in self.keys
    def is_mud(self, x, y): return (x,y) in self.mud_puddles
    def is_water(self, x, y): return (x,y) in self.water_cells
    def is_portal(self, x, y): return (x,y) in self.portal_locations
    def get_portal_target(self, x, y): return self.portals.get((x,y), {}).get('target')

    def remove_key(self, x, y):
        key_pos = (x, y)
        if key_pos in self.keys: 
            self.keys.remove(key_pos)
            return True
        return False

    def update(self, dt):
        if self.min_loaded_portal_frames > 0: 
            self.portal_animation_timer += dt
            if self.portal_animation_timer >= PORTAL_ANIMATION_SPEED:
                self.portal_animation_timer %= PORTAL_ANIMATION_SPEED # More robust reset
                self.portal_current_frame_index = (self.portal_current_frame_index + 1) % self.min_loaded_portal_frames

    def draw(self, surface):
        # Draw base maze: walls and paths/mud/water
        for y_draw in range(self.height):
            for x_draw in range(self.width):
                rect = pygame.Rect(x_draw * self.cell_size, y_draw * self.cell_size, self.cell_size, self.cell_size)
                pos = (x_draw, y_draw)

                if self.maze_data[y_draw][x_draw] == 1: 
                    pygame.draw.rect(surface, WALL_COLOR, rect)
                elif pos in self.water_cells:
                    if self.use_water_texture: surface.blit(self.water_img, rect)
                    else: pygame.draw.rect(surface, WATER_COLOR, rect) # Fallback color
                elif pos in self.mud_puddles:
                    if self.use_mud_texture: surface.blit(self.mud_img, rect)
                    else: pygame.draw.rect(surface, MUD_COLOR, rect) # Fallback color
                else: # Path cell (could be start, exit, or just empty path)
                    if self.use_path_texture: surface.blit(self.path_img, rect)
                    else: pygame.draw.rect(surface, PATH_COLOR, rect) # Fallback color
        
        # Draw Portals on top
        for pos, data in self.portals.items():
            rect = pygame.Rect(pos[0] * self.cell_size, pos[1] * self.cell_size, self.cell_size, self.cell_size)
            pair_id = data['pair_id']
            
            if self.portal_pair_use_texture.get(pair_id) and \
               self.portal_pair_frames.get(pair_id) and \
               self.min_loaded_portal_frames > 0:
                
                frames_for_this_pair = self.portal_pair_frames[pair_id]
                current_idx_for_pair = self.portal_current_frame_index % len(frames_for_this_pair)
                img_to_draw = frames_for_this_pair[current_idx_for_pair]
                surface.blit(img_to_draw, rect)
            else: # Fallback drawing for portal
                pygame.draw.rect(surface, data.get('color', PORTAL_COLORS_FALLBACK[0]), rect)
                inner_rect = rect.inflate(-self.cell_size // 4, -self.cell_size // 4)
                # Simple pulsing effect for fallback
                alpha = 80 + (pygame.time.get_ticks() // 20) % 70 # Gentle pulse
                try:
                    pygame.draw.ellipse(surface, (*DMG_PRIMARY_GREEN[:3], alpha), inner_rect)
                except TypeError: # For Pygames that don't handle alpha in tuple well for draw
                     ellipse_color = pygame.Color(*DMG_PRIMARY_GREEN[:3])
                     ellipse_color.a = alpha
                     pygame.draw.ellipse(surface, ellipse_color, inner_rect)


        # Draw Exit
        exit_rect = pygame.Rect(self.exit_pos[0] * self.cell_size, self.exit_pos[1] * self.cell_size, self.cell_size, self.cell_size)
        if self.use_exit_texture:
            surface.blit(self.exit_img, exit_rect)
        else: # Themed Fallback drawing for exit
            pygame.draw.rect(surface, EXIT_COLOR, exit_rect)
            # Simple door icon
            door_knob_radius = self.cell_size // 8
            pygame.draw.rect(surface, DMG_DARK_BG, exit_rect.inflate(-self.cell_size//3, -self.cell_size//6)) # Door panel
            pygame.draw.circle(surface, DMG_ACCENT_GREEN, 
                               (exit_rect.centerx + self.cell_size//5, exit_rect.centery), 
                               door_knob_radius) # Knob

        # Draw Keys
        key_img_to_draw = self.key_img
        key_draw_size = key_img_to_draw.get_size()
        key_offset_x = (self.cell_size - key_draw_size[0]) // 2
        key_offset_y = (self.cell_size - key_draw_size[1]) // 2

        for kx, ky in self.keys:
            key_pos_on_screen = (kx * self.cell_size + key_offset_x, ky * self.cell_size + key_offset_y)
            if self.use_key_texture:
                surface.blit(key_img_to_draw, key_pos_on_screen)
            else: # Themed Fallback drawing for key
                center_x = kx * self.cell_size + self.cell_size // 2
                center_y = ky * self.cell_size + self.cell_size // 2
                radius = int(self.cell_size * 0.38)
                # Key shape
                pygame.draw.circle(surface, KEY_COLOR, (center_x, center_y - radius // 2), radius // 2) # Head
                pygame.draw.rect(surface, KEY_COLOR, pygame.Rect(center_x - radius//6, center_y - radius//3, radius//3, radius * 1.2)) # Shaft
                pygame.draw.rect(surface, KEY_COLOR, pygame.Rect(center_x - radius//3, center_y + radius *0.6, radius*2//3, radius//4)) # Bit


    def get_total_keys_placed(self): return self.actual_num_keys if hasattr(self, 'actual_num_keys') else len(self.keys)