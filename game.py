# game.py
import pygame
import sys
import time
import math
import os
from collections import deque
import traceback

from constants import * 
from maze import Maze
from player import Player 
from solvers.bfs_solver import BFSSolver
from solvers.greedy_solver import GreedySolver
from solvers.simulated_annealing_solver import SimulatedAnnealingSolver
from solvers.local_beam_search_solver import LocalBeamSearchSolver
from solvers.spo_solver import SPOSolver
from solvers.csp_backtracking_fc_solver import CSPBacktrackingFCSolver
from solvers.q_learning_solver import QLearningSolver
import solvers 

from utils import load_sound, draw_rounded_rect, draw_text, load_scaled_image

class AlgorithmRunner:
    def __init__(self, solver_instance, maze_instance, game_speed_ref: list[float]):
        self.solver = solver_instance
        self.maze = maze_instance
        self.name = solver_instance.__class__.__name__.replace("Solver", "")
        self.state = "IDLE"
        self.think_timer = 0.0
        self.required_think_time = 0.0
        self.path_to_follow = []
        self.current_path_index = 0
        self.move_timer = 0.0
        self.algo_player_pos = self.solver.start_pos
        self.prev_algo_player_pos = self.solver.start_pos

        self.results = None
        self.start_time_solve = 0
        self.visualize_search = True
        self.visualization_complete = False
        self.key_pickup_sound = load_sound(KEY_PICKUP_SOUND)
        self.keys_sound_played_for = set()
        self.game_speed_ref = game_speed_ref

        self.cell_size = CELL_SIZE
        self._load_sprites()
        self.direction = 'right'
        self.is_moving_for_animation = False
        self.animation_timer = 0.0
        self.current_frame_index = 0
        self.current_image = self.idle_img_right

    def _load_sprites(self):
        self.idle_img_right = load_scaled_image(PLAYER_IDLE_IMAGE, self.cell_size)
        if self.idle_img_right.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR) and not os.path.exists(os.path.join(IMAGE_FOLDER,PLAYER_IDLE_IMAGE)):
            print(f"W: Algo Player idle image '{PLAYER_IDLE_IMAGE}' not found. Using fallback.", file=sys.stderr)
            self.idle_img_right = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            self.idle_img_right.fill(DMG_PRIMARY_GREEN)
            pygame.draw.circle(self.idle_img_right, DMG_LIGHT_TEXT, (self.cell_size//2, self.cell_size//2), self.cell_size//3)
        self.idle_img_left = pygame.transform.flip(self.idle_img_right, True, False)

        self.walk_frames_right = []
        MAX_ALGO_WALK_FRAMES = 8
        for i in range(MAX_ALGO_WALK_FRAMES):
            filename = f"{PLAYER_WALK_PREFIX}{i}.png"
            image_path = os.path.join(IMAGE_FOLDER, filename)
            if not os.path.exists(image_path):
                if i == 0:
                    print(f"W: Algo Player walk frame '{filename}' (start of sequence) not found. Walk animation may be missing.", file=sys.stderr)
                break
            frame = load_scaled_image(filename, self.cell_size)
            if frame.get_at((0,0)) == pygame.Color(FALLBACK_IMAGE_COLOR):
                print(f"W: Error loading Algo Player walk frame '{filename}' (file exists but failed to load). Stopping sequence.", file=sys.stderr)
                break
            self.walk_frames_right.append(frame)

        if not self.walk_frames_right:
            print(f"W: No Algo Player walk frames. Using idle image for walking.", file=sys.stderr)
            self.walk_frames_right.append(self.idle_img_right)
        self.walk_frames_left = [pygame.transform.flip(img, True, False) for img in self.walk_frames_right]


    def _update_animation(self, dt: float):
        effective_dt = dt * self.game_speed_ref[0]
        effective_algo_animation_speed = PLAYER_ANIMATION_SPEED / self.game_speed_ref[0]

        self.animation_timer += effective_dt
        if self.animation_timer >= effective_algo_animation_speed:
            self.animation_timer %= effective_algo_animation_speed

            if self.is_moving_for_animation:
                walk_frames = self.walk_frames_right if self.direction == 'right' else self.walk_frames_left
                if walk_frames:
                    self.current_frame_index = (self.current_frame_index + 1) % len(walk_frames)
            else:
                self.current_frame_index = 0

        if not self.is_moving_for_animation:
            self.current_image = self.idle_img_right if self.direction == 'right' else self.idle_img_left
        elif self.is_moving_for_animation and self.walk_frames_right:
             walk_frames_current_dir = self.walk_frames_right if self.direction == 'right' else self.walk_frames_left
             if walk_frames_current_dir:
                idx_to_use = self.current_frame_index % len(walk_frames_current_dir)
                self.current_image = walk_frames_current_dir[idx_to_use]
             else:
                self.current_image = self.idle_img_right if self.direction == 'right' else self.idle_img_left


    def start_solving_process(self):
        self.state = "THINKING"
        self.think_timer = 0.0
        self.visualization_complete = False
        self.path_to_follow = []
        self.current_path_index = 0
        self.prev_algo_player_pos = self.solver.start_pos
        self.algo_player_pos = self.solver.start_pos
        self.keys_sound_played_for.clear()
        self.is_moving_for_animation = False
        self.direction = 'right'
        self.current_image = self.idle_img_right

        if hasattr(self.solver, 'path'): self.solver.path = []
        if hasattr(self.solver, 'total_cost'): self.solver.total_cost = 0
        if hasattr(self.solver, 'nodes_expanded'): self.solver.nodes_expanded = 0
        if hasattr(self.solver, 'path_found'): self.solver.path_found = False
        if hasattr(self.solver, 'came_from'): self.solver.came_from = {}
        if hasattr(self.solver, 'cost_so_far'): self.solver.cost_so_far = {}
        
        if isinstance(self.solver, QLearningSolver):
            pass

        self.start_time_solve = time.time()
        self.solver.solve_all_stages() 
        self.results = self.solver.get_solver_results()

        effective_think_time_per_node = ALGORITHM_THINK_TIME_PER_NODE / self.game_speed_ref[0]
        self.required_think_time = self.results.get("nodes_expanded", 0) * effective_think_time_per_node
        if self.results and self.results.get("path_found") and self.required_think_time == 0:
             self.required_think_time = 0.1 / self.game_speed_ref[0]

        if self.visualize_search:
            solver_specific_flags_to_reset = [
                '_viz_initialized_bfs', '_viz_initialized_greedy', '_viz_initialized_astar',
                '_sa_visualization_solve_done', '_lbs_visualization_solve_done',
                '_spo_solve_complete', '_csp_solve_complete', '_csp_viz_has_run_once',
                '_solve_run_started_viz' 
            ]
            for flag_name in solver_specific_flags_to_reset:
                if hasattr(self.solver, flag_name):
                    if flag_name.endswith("_done") or flag_name.endswith("_once") or flag_name.startswith("_solve_run"):
                        if flag_name in self.solver.__dict__: delattr(self.solver, flag_name)
                    else:
                        setattr(self.solver, flag_name, False)

            if hasattr(self.solver, 'viz_visited_nodes'): self.solver.viz_visited_nodes = set()
            if hasattr(self.solver, 'viz_frontier'):
                if isinstance(self.solver.viz_frontier, deque): self.solver.viz_frontier.clear()
            if hasattr(self.solver, 'viz_frontier_heap'): self.solver.viz_frontier_heap = []

            if isinstance(self.solver, QLearningSolver):
                 self.solver._training_complete = False 
                 self.solver._current_episode = 0
                 if hasattr(self.solver, '_solve_run_started_viz'): 
                     if '_solve_run_started_viz' in self.solver.__dict__:
                         delattr(self.solver, '_solve_run_started_viz')
                 if hasattr(self.solver, 'viz_current_runtime_path_idx'):
                     self.solver.viz_current_runtime_path_idx = 0
                 if hasattr(self.solver, 'viz_current_training_path'): 
                     self.solver.viz_current_training_path = []
                 self.solver.viz_agent_pos = self.solver.start_pos
            self.visualization_complete = False
        else:
            self.visualization_complete = True


    def update(self, dt):
        effective_dt = dt * self.game_speed_ref[0]
        effective_algo_move_speed = ALGORITHM_MOVE_SPEED / self.game_speed_ref[0]
        self.prev_algo_player_pos = self.algo_player_pos

        if self.state == "THINKING":
            self.is_moving_for_animation = False 
            if self.visualize_search and not self.visualization_complete:
                pos_before_viz_step = self.algo_player_pos
                if isinstance(self.solver, QLearningSolver) and hasattr(self.solver, 'viz_agent_pos'):
                    pos_before_viz_step = self.solver.viz_agent_pos
                self.visualization_complete = self.solver.solve_step_visualize()
                current_pos_after_viz_step = pos_before_viz_step 
                if isinstance(self.solver, QLearningSolver) and hasattr(self.solver, 'viz_agent_pos'):
                    current_pos_after_viz_step = self.solver.viz_agent_pos
                self.algo_player_pos = current_pos_after_viz_step
                if self.algo_player_pos != pos_before_viz_step:
                    self.is_moving_for_animation = True
                else:
                    self.is_moving_for_animation = False
            if self.visualization_complete: 
                self.is_moving_for_animation = False 
                self.think_timer += effective_dt
                if self.think_timer >= self.required_think_time:
                    if self.results and self.results.get("path_found"):
                        self.path_to_follow = self.results.get("path", [])
                        if self.path_to_follow:
                            self.algo_player_pos = self.path_to_follow[0] 
                            self.current_path_index = 0
                            self.state = "MOVING"; self.move_timer = 0.0
                            if self.maze.is_key(self.algo_player_pos[0], self.algo_player_pos[1]) and \
                               self.algo_player_pos not in self.keys_sound_played_for:
                                if self.key_pickup_sound: self.key_pickup_sound.play()
                                self.keys_sound_played_for.add(self.algo_player_pos)
                        else: self.state = "FAILED"
                    else: self.state = "FAILED"
        elif self.state == "MOVING":
            self.is_moving_for_animation = True
            self.move_timer += effective_dt
            current_algo_move_delay = effective_algo_move_speed
            if self.maze.is_mud(self.algo_player_pos[0], self.algo_player_pos[1]):
                current_algo_move_delay *= PLAYER_MUD_MULTIPLIER
            if self.move_timer >= current_algo_move_delay:
                self.move_timer = 0.0
                self.current_path_index += 1
                if self.current_path_index < len(self.path_to_follow):
                    self.algo_player_pos = self.path_to_follow[self.current_path_index]
                    if self.maze.is_key(self.algo_player_pos[0], self.algo_player_pos[1]) and \
                       self.algo_player_pos not in self.keys_sound_played_for:
                        if self.key_pickup_sound: self.key_pickup_sound.play()
                        self.keys_sound_played_for.add(self.algo_player_pos)
                else:
                    self.state = "FINISHED"
                    self.is_moving_for_animation = False
        else: self.is_moving_for_animation = False

        dx = self.algo_player_pos[0] - self.prev_algo_player_pos[0]
        if dx > 0: self.direction = 'right'
        elif dx < 0: self.direction = 'left'
        self._update_animation(dt)

    def draw(self, surface):
        if self.state == "THINKING" and self.visualize_search and not self.visualization_complete:
            if hasattr(self.solver, 'viz_visited_nodes') and self.solver.viz_visited_nodes:
                for pos_v in self.solver.viz_visited_nodes:
                    rect_v = pygame.Rect(pos_v[0] * CELL_SIZE, pos_v[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    s_v = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s_v.fill(VISITED_NODE_COLOR_ALGO)
                    surface.blit(s_v, rect_v.topleft)
            current_visual_frontier_nodes = []
            if hasattr(self.solver, 'viz_frontier') and self.solver.viz_frontier:
                 if isinstance(self.solver.viz_frontier, deque):
                    current_visual_frontier_nodes = list(self.solver.viz_frontier)
            elif hasattr(self.solver, 'viz_frontier_heap') and self.solver.viz_frontier_heap:
                 current_visual_frontier_nodes = [item[2] for item in self.solver.viz_frontier_heap if len(item) > 2 and isinstance(item[2], tuple)]
            for pos_f in current_visual_frontier_nodes:
                if isinstance(pos_f, tuple) and len(pos_f) == 2: 
                    rect_f = pygame.Rect(pos_f[0] * CELL_SIZE, pos_f[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    s_f = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s_f.fill(FRONTIER_NODE_COLOR_ALGO)
                    surface.blit(s_f, rect_f.topleft)
            if hasattr(self.solver, 'path') and self.solver.path and len(self.solver.path) > 1:
                 try:
                    pygame.draw.lines(surface, FINAL_PATH_COLOR_ALGO[:3], False,
                                     [(p[0]*CELL_SIZE+CELL_SIZE//2, p[1]*CELL_SIZE+CELL_SIZE//2) for p in self.solver.path], 2)
                 except Exception: pass 
        path_list_final = []
        if self.results and self.results.get("path_found"):
            path_list_final = self.results.get("path", [])
        if path_list_final and len(path_list_final) > 1 and \
           ((self.state == "THINKING" and self.visualization_complete) or self.state in ["MOVING", "FINISHED"]):
            try:
                pygame.draw.lines(surface, FINAL_PATH_COLOR_ALGO[:3], False,
                                 [(p[0]*CELL_SIZE+CELL_SIZE//2, p[1]*CELL_SIZE+CELL_SIZE//2) for p in path_list_final], 3)
            except Exception: pass
        if self.state != "IDLE":
            draw_x = self.algo_player_pos[0] * self.cell_size
            draw_y = self.algo_player_pos[1] * self.cell_size
            surface.blit(self.current_image, (draw_x, draw_y))
        if self.state == "FAILED":
            font = pygame.font.SysFont(None, UI_FONT_SIZE_LARGE)
            text_surf = font.render(f"{self.name}: No Path Found", True, NO_PATH_FOUND_COLOR[:3])
            game_surface_width = surface.get_width()
            game_surface_height = surface.get_height()
            text_rect = text_surf.get_rect(center=(game_surface_width // 2, game_surface_height // 2))
            bg_rect = text_rect.inflate(UI_PADDING * 2, UI_PADDING)
            draw_rounded_rect(surface, (*DMG_DARK_BG, 230), bg_rect, UI_ROUND_RECT_RADIUS, 2, DMG_WARN_TEXT[:3])
            surface.blit(text_surf, text_rect)

    def get_status_text(self):
        if self.state == "THINKING":
            if self.visualize_search and not self.visualization_complete:
                if isinstance(self.solver, QLearningSolver):
                    if not self.solver._training_complete:
                        return f"{self.name}: Training Ep {self.solver._current_episode}/{self.solver.num_episodes}"
                    else: 
                        current_step_in_viz = getattr(self.solver, 'viz_current_runtime_path_idx', 0)
                        total_steps_in_path = len(self.solver.path) if hasattr(self.solver, 'path') and self.solver.path else 0
                        return f"{self.name}: Visualizing Policy (Step {current_step_in_viz}/{max(0,total_steps_in_path-1)})"
                nodes_viz = 0
                if hasattr(self.solver, 'nodes_expanded'): 
                    nodes_viz = self.solver.nodes_expanded
                return f"{self.name}: Visualizing ({nodes_viz} steps/nodes)..."
            progress = (self.think_timer / self.required_think_time * 100) if self.required_think_time > 0 else 0
            if self.required_think_time == 0 and self.results and self.results.get("path_found"): progress = 100
            nodes_final = self.results.get("nodes_expanded", 0) if self.results else 0
            return f"{self.name}: Processing ({min(100, int(progress))}% of {nodes_final} nodes)"
        elif self.state == "MOVING":
            path_len = len(self.path_to_follow) -1 if self.path_to_follow else 0
            return f"{self.name}: Moving... ({self.current_path_index}/{path_len})"
        elif self.state == "FINISHED":
            cost = self.results.get('cost', 'N/A') if self.results else 'N/A'
            steps = self.results.get('steps', 'N/A') if self.results else (len(self.path_to_follow)-1 if self.path_to_follow else 0)
            return f"{self.name}: Finished! Cost: {cost}, Steps: {steps}"
        elif self.state == "FAILED": return f"{self.name}: Failed to find path."
        return f"{self.name}: Ready"

    def is_done(self): return self.state == "FINISHED" or self.state == "FAILED"
    def get_final_results(self): return self.results

class Game:
    def __init__(self):
        try:
            pygame.init()
            if pygame.mixer and not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.font.init()
        except pygame.error as e:
            print(f"Pygame Init Error: {e}", file=sys.stderr); sys.exit(1)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ESCAPE ROOM - Revamped UI")
        self.clock = pygame.time.Clock()
        self.running = True
        self.maze_area_rect = pygame.Rect(UI_PADDING, UI_PADDING, MAZE_AREA_WIDTH - 2 * UI_PADDING, MAZE_AREA_HEIGHT - 2 * UI_PADDING)
        self.info_area_rect = pygame.Rect(self.maze_area_rect.right + UI_PADDING, UI_PADDING, INFO_AREA_WIDTH - UI_PADDING, MAZE_AREA_HEIGHT - 2 * UI_PADDING)
        self.controls_area_rect = pygame.Rect(UI_PADDING, self.maze_area_rect.bottom + UI_PADDING, SCREEN_WIDTH - 2 * UI_PADDING, CONTROLS_AREA_HEIGHT - UI_PADDING)
        self.maze_render_surface = pygame.Surface((MAZE_WIDTH * CELL_SIZE, MAZE_HEIGHT * CELL_SIZE))
        self.game_state = "IDLE_CONFIG"
        self.maze = None
        self.player = None
        self.algorithm_runner = None
        self.font_xl = pygame.font.SysFont(None, UI_FONT_SIZE_XLARGE)
        self.font_l = pygame.font.SysFont(None, UI_FONT_SIZE_LARGE)
        self.font_m = pygame.font.SysFont(None, UI_FONT_SIZE_NORMAL)
        self.font_s = pygame.font.SysFont(None, UI_FONT_SIZE_SMALL)
        self.font_xs = pygame.font.SysFont(None, UI_FONT_SIZE_XSMALL)
        self.solver_classes = {"Player": None, "BFS": BFSSolver, "Greedy": GreedySolver, "A*": solvers.a_star_solver.AStarSolver, "SA": SimulatedAnnealingSolver, "LBS": LocalBeamSearchSolver, "SPO": SPOSolver, "CSP_FC": CSPBacktrackingFCSolver, "Q-Learn": QLearningSolver,}
        self.selected_algo_name = "Player"
        self.num_keys_setting = DEFAULT_NUM_KEYS
        self.game_speed_multiplier = [1.0]
        self.speed_slider_options = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
        self.current_speed_option_idx = self.speed_slider_options.index(1.0)
        self._init_control_ui_elements()
        self.player_start_time = 0
        self.show_missing_keys_msg = False
        self.missing_keys_msg_text = ""
        self.controls_status_message = "Welcome! Regenerate maze or select mode."
        self.outcome_display_timer = 0.0
        self.game_reports = []
        self.current_required_keys = self.num_keys_setting
        self.current_maze_run_history = []
        self.transition_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.transition_surface.fill(DMG_DARK_BG)
        self.transition_alpha = 0
        self.fading_out = False
        self.fading_in = False
        self.next_game_state_after_fade = ""
        
        self.gameplay_music_file = GAMEPLAY_MUSIC
        self.menu_music_file = MENU_MUSIC
        self.current_music_playing = None 
        self.previous_game_state_for_music = None 

    def _init_control_ui_elements(self):
        base_y = self.controls_area_rect.top + UI_SECTION_PADDING // 2 + self.font_s.get_height() + UI_ELEMENT_PADDING
        element_height = UI_BUTTON_HEIGHT
        algo_section_x_start = self.controls_area_rect.left + UI_ELEMENT_PADDING
        self.algo_section_label = {"text": "Solver Mode", "font": self.font_s, "color": DMG_PRIMARY_GREEN}
        self.algo_section_label_pos = (algo_section_x_start, self.controls_area_rect.top + UI_PADDING // 2)
        arrow_btn_width = element_height // 1.5
        self.algo_scroll_left_arrow_rect = pygame.Rect(algo_section_x_start, base_y, arrow_btn_width, element_height)
        self.algo_names_list = list(self.solver_classes.keys())
        self.current_algo_scroll_idx = 0
        self.num_algos_to_display = 3
        algo_section_width_estimate = self.controls_area_rect.width * 0.35
        algo_buttons_total_width = algo_section_width_estimate - (arrow_btn_width * 2) - (UI_ELEMENT_PADDING * 3)
        self.algo_button_width = (algo_buttons_total_width - (self.num_algos_to_display -1) * UI_ELEMENT_PADDING ) / self.num_algos_to_display
        self.algo_button_width = max(80, int(self.algo_button_width))
        self.algo_display_x_start = self.algo_scroll_left_arrow_rect.right + UI_ELEMENT_PADDING
        current_algo_end_x = self.algo_display_x_start + self.num_algos_to_display * self.algo_button_width + (self.num_algos_to_display - 1) * UI_ELEMENT_PADDING
        self.algo_scroll_right_arrow_rect = pygame.Rect(current_algo_end_x + UI_ELEMENT_PADDING, base_y, arrow_btn_width, element_height)
        config_section_x_start = self.algo_scroll_right_arrow_rect.right + UI_SECTION_PADDING
        self.config_section_label = {"text": "Maze Parameters", "font": self.font_s, "color": DMG_PRIMARY_GREEN}
        self.config_section_label_pos = (config_section_x_start, self.controls_area_rect.top + UI_PADDING //2)
        self.key_selector_elements = {}
        key_label_text = "Keys:"
        key_label_surf = self.font_s.render(key_label_text, True, DMG_LIGHT_TEXT)
        key_label_rect = key_label_surf.get_rect(left=config_section_x_start, centery=base_y + element_height // 2)
        self.key_selector_elements["label_surf"] = key_label_surf
        self.key_selector_elements["label_rect"] = key_label_rect
        key_input_x = key_label_rect.right + UI_ELEMENT_PADDING
        btn_size_small = int(element_height * 0.7)
        self.key_selector_elements["minus_rect"] = pygame.Rect(key_input_x, base_y + (element_height - btn_size_small)//2, btn_size_small, btn_size_small)
        key_display_width = 50
        self.key_selector_elements["display_rect"] = pygame.Rect(self.key_selector_elements["minus_rect"].right + UI_ELEMENT_PADDING//2, base_y, key_display_width, element_height)
        self.key_selector_elements["plus_rect"] = pygame.Rect(self.key_selector_elements["display_rect"].right + UI_ELEMENT_PADDING//2, base_y + (element_height - btn_size_small)//2, btn_size_small, btn_size_small)
        speed_section_x_start = self.key_selector_elements["plus_rect"].right + UI_ELEMENT_PADDING * 2
        self.speed_slider_elements = {}
        speed_label_text = "Speed:"
        speed_label_surf = self.font_s.render(speed_label_text, True, DMG_LIGHT_TEXT)
        speed_label_rect = speed_label_surf.get_rect(left=speed_section_x_start, centery=base_y + element_height // 2)
        self.speed_slider_elements["label_surf"] = speed_label_surf
        self.speed_slider_elements["label_rect"] = speed_label_rect
        slider_x = speed_label_rect.right + UI_ELEMENT_PADDING
        slider_width = 120
        self.speed_slider_elements["bar_rect"] = pygame.Rect(slider_x, base_y + element_height // 2 - UI_SLIDER_TRACK_HEIGHT // 2, slider_width, UI_SLIDER_TRACK_HEIGHT)
        self.speed_slider_elements["knob_radius"] = UI_SLIDER_KNOB_RADIUS
        speed_val_display_width = self.font_xs.size("8.00x")[0] + UI_ELEMENT_PADDING
        self.speed_slider_elements["value_text_pos_x"] = self.speed_slider_elements["bar_rect"].right + UI_ELEMENT_PADDING // 2
        reset_btn_size = btn_size_small
        self.speed_slider_elements["reset_rect"] = pygame.Rect(self.speed_slider_elements["value_text_pos_x"] + speed_val_display_width, base_y + (element_height - reset_btn_size)//2, reset_btn_size, reset_btn_size)
        action_section_x_start = self.speed_slider_elements["reset_rect"].right + UI_SECTION_PADDING
        self.action_section_label = {"text": "Actions", "font": self.font_s, "color": DMG_PRIMARY_GREEN}
        self.action_section_label_pos = (action_section_x_start, self.controls_area_rect.top + UI_PADDING //2)
        self.regenerate_button = {}
        regen_btn_width = self.font_m.size("Regenerate")[0] + UI_PADDING * 2
        self.regenerate_button["rect"] = pygame.Rect(action_section_x_start, base_y, regen_btn_width, element_height)
        self.regenerate_button["text"] = "Regenerate"
        self.start_run_button = {}
        start_btn_width = self.font_m.size("Start Run")[0] + UI_PADDING * 3
        self.start_run_button["rect"] = pygame.Rect(self.regenerate_button["rect"].right + UI_ELEMENT_PADDING, base_y, start_btn_width, element_height)
        self.start_run_button["text"] = "Start Run"
        self.compare_button = {}
        compare_btn_width = self.font_m.size("Compare")[0] + UI_PADDING * 2
        self.compare_button["rect"] = pygame.Rect(self.start_run_button["rect"].right + UI_ELEMENT_PADDING, base_y, compare_btn_width, element_height)
        self.compare_button["text"] = "Compare"
        self.controls_status_rect = pygame.Rect(self.controls_area_rect.left, self.controls_area_rect.bottom - self.font_xs.get_height() - UI_PADDING // 2, self.controls_area_rect.width, self.font_xs.get_height() + UI_PADDING // 2)

    def _play_new_music(self, music_type):
        if not pygame.mixer.get_init():
            print("W: Mixer not initialized, cannot play music.", file=sys.stderr)
            return

        target_file_name = None
        if music_type == "gameplay":
            target_file_name = self.gameplay_music_file
        elif music_type == "menu":
            target_file_name = self.menu_music_file
        else:
            print(f"W: Unknown music type '{music_type}'", file=sys.stderr)
            return

        if self.current_music_playing == music_type and pygame.mixer.music.get_busy():
            return 

        try:
            music_path = os.path.join(SOUNDS_FOLDER, target_file_name)
            if not os.path.exists(music_path):
                print(f"W: Music file not found: {music_path}", file=sys.stderr)
                pygame.mixer.music.stop()
                self.current_music_playing = None
                return
            
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1) 
            self.current_music_playing = music_type
        except pygame.error as e:
            print(f"ERROR playing music '{target_file_name}': {e}", file=sys.stderr)
            self.current_music_playing = None
            
    def _manage_music_transition(self, new_state, old_state):
        if new_state == "COMPARING_RESULTS" and old_state != "COMPARING_RESULTS":
            if self.current_music_playing != "menu":
                self._play_new_music("menu")
        elif old_state == "COMPARING_RESULTS" and new_state != "COMPARING_RESULTS":
            if self.current_music_playing != "gameplay":
                self._play_new_music("gameplay")
        elif new_state != "COMPARING_RESULTS" and self.current_music_playing != "gameplay":
            self._play_new_music("gameplay")


    def _initiate_fade_to_state(self, new_state):
        if self.game_state != new_state and not self.fading_out and not self.fading_in:
            self.fading_out = True; self.fading_in = False
            self.transition_alpha = 0; self.next_game_state_after_fade = new_state
            
    def _update_fades(self, dt):
        if self.fading_out:
            self.transition_alpha += FADE_SPEED
            if self.transition_alpha >= 255:
                self.transition_alpha = 255
                self.fading_out = False
                
                self.previous_game_state_for_music = self.game_state 
                self.game_state = self.next_game_state_after_fade
                
                if self.previous_game_state_for_music.startswith("PLAYING_") and self.game_state == "IDLE_CONFIG":
                     self._reset_game_specific_state(reset_maze=False)
                elif self.game_state == "IDLE_CONFIG_POST_REGEN":
                     self.game_state = "IDLE_CONFIG"; self._reset_game_specific_state(reset_maze=False)
                
                self._manage_music_transition(self.game_state, self.previous_game_state_for_music)
                
                self.fading_in = True
        elif self.fading_in:
            self.transition_alpha -= FADE_SPEED
            if self.transition_alpha <= 0: 
                self.transition_alpha = 0
                self.fading_in = False
                self.next_game_state_after_fade = ""
                self._manage_music_transition(self.game_state, self.previous_game_state_for_music)


    def _calculate_feature_count(self, num_keys, base, per_key_factor, max_density_ratio):
        effective_num_keys = max(0, num_keys)
        count_from_keys = base + per_key_factor * (effective_num_keys - (MIN_NUM_KEYS_CONFIG if MIN_NUM_KEYS_CONFIG >=0 else 0))
        count = max(base, count_from_keys)
        path_area_estimate = (MAZE_WIDTH - 2) * (MAZE_HEIGHT - 2) * 0.45
        max_allowed_by_density = int(path_area_estimate * max_density_ratio)
        return max(0, min(int(count), max_allowed_by_density))

    def _regenerate_maze_action(self):
        keys_requested = self.num_keys_setting
        if self.selected_algo_name == "SPO": keys_requested = 0
        print(f"\n--- Regenerating Maze ---"); print(f"Keys Requested: {keys_requested}")
        self._reset_game_specific_state(reset_maze=True)
        self.current_maze_run_history = []
        num_puddles = self._calculate_feature_count(keys_requested, BASE_PUDDLES, PUDDLES_PER_KEY_INCREASE, MAX_PUDDLE_DENSITY)
        num_slides = self._calculate_feature_count(keys_requested, BASE_SLIDES, SLIDES_PER_KEY_INCREASE, MAX_SLIDE_DENSITY)
        num_portal_pairs_calc = keys_requested // 2 if keys_requested > 0 else 0
        num_portal_pairs = min(num_portal_pairs_calc, MAX_PORTAL_PAIRS if MAX_PORTAL_PAIRS >=0 else 0)
        try:
            self.maze = Maze(MAZE_WIDTH, MAZE_HEIGHT, CELL_SIZE, keys_requested, num_puddles, num_slides, num_portal_pairs, MAZE_LOOP_CHANCE)
            self.current_required_keys = self.maze.get_total_keys_placed()
            self.controls_status_message = f"Maze Generated! Keys: {self.current_required_keys}. Select mode."
            print(f"Maze generated. Actual Keys: {self.current_required_keys}, Puddles: {getattr(self.maze, 'actual_num_puddles', 'N/A')}, Slides: {getattr(self.maze, 'actual_num_slides', 'N/A')}, Portals: {getattr(self.maze, 'actual_num_portal_pairs', 'N/A')} pairs")
            self._initiate_fade_to_state("IDLE_CONFIG_POST_REGEN")
        except Exception as e:
            self.controls_status_message = "Error: Maze generation failed."
            print(f"FATAL: Maze creation failed: {e}", file=sys.stderr); traceback.print_exc()
            self.maze = None; self._initiate_fade_to_state("IDLE_CONFIG")

    def _start_run_action(self):
        if not self.maze: self.controls_status_message = "Error: No maze. Regenerate first."; return
        self.controls_status_message = f"Running: {self.selected_algo_name}..."
        print(f"\n--- Starting Run ---"); print(f"Mode: {self.selected_algo_name}")
        self._reset_game_specific_state(reset_maze=False)
        if self.selected_algo_name == "Player":
            self.player = Player(self.maze.start_pos[0], self.maze.start_pos[1], CELL_SIZE, self.game_speed_multiplier)
            self.player.reset_state()
            self._initiate_fade_to_state("PLAYING_PLAYER")
            self.player_start_time = time.time()
        else:
            SolverClass = self.solver_classes.get(self.selected_algo_name)
            if SolverClass:
                try:
                    solver_instance = SolverClass(self.maze)
                    self.algorithm_runner = AlgorithmRunner(solver_instance, self.maze, self.game_speed_multiplier)
                    self.algorithm_runner.start_solving_process()
                    self._initiate_fade_to_state("PLAYING_ALGORITHM")
                except Exception as e:
                    self.controls_status_message = f"Error: Failed to init {self.selected_algo_name}."
                    print(f"Error initializing solver '{self.selected_algo_name}': {e}", file=sys.stderr); traceback.print_exc()
                    self._initiate_fade_to_state("IDLE_CONFIG"); return
            else:
                self.controls_status_message = f"Error: Solver {self.selected_algo_name} not found."
                print(f"Error: Solver class for '{self.selected_algo_name}' not found.", file=sys.stderr)
                self._initiate_fade_to_state("IDLE_CONFIG"); return
        self.outcome_display_timer = 0.0

    def _reset_game_specific_state(self, reset_maze=False):
        if reset_maze: self.maze = None; self.current_maze_run_history = []
        self.player = None; self.algorithm_runner = None
        self.show_missing_keys_msg = False; self.missing_keys_msg_text = ""
        self.outcome_display_timer = 0.0
        if self.game_state == "IDLE_CONFIG" or reset_maze: self.controls_status_message = "Ready. Select mode or Regenerate." if self.maze else "Regenerate maze to begin."

    def _handle_input(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.game_state.startswith("PLAYING_") or self.game_state.startswith("OUTCOME_") or self.game_state == "COMPARING_RESULTS":
                        self._initiate_fade_to_state("IDLE_CONFIG"); self.controls_status_message = "Run ended. Select new mode or regenerate."
                    elif self.game_state == "IDLE_CONFIG": self.running = False
                elif self.game_state == "COMPARING_RESULTS" and event.key in [pygame.K_RETURN, pygame.K_SPACE]: self._initiate_fade_to_state("IDLE_CONFIG")
                elif self.game_state == "IDLE_CONFIG" or self.game_state.startswith("OUTCOME_") or self.game_state == "COMPARING_RESULTS":
                    current_selected_algo_idx_in_list = -1
                    try: current_selected_algo_idx_in_list = self.algo_names_list.index(self.selected_algo_name)
                    except ValueError: pass
                    if event.key == pygame.K_LEFT:
                        if current_selected_algo_idx_in_list > 0:
                            self.selected_algo_name = self.algo_names_list[current_selected_algo_idx_in_list - 1]
                            if current_selected_algo_idx_in_list - 1 < self.current_algo_scroll_idx: self.current_algo_scroll_idx = max(0, current_selected_algo_idx_in_list - 1)
                        elif self.current_algo_scroll_idx > 0 : self.current_algo_scroll_idx -=1
                    elif event.key == pygame.K_RIGHT:
                        if current_selected_algo_idx_in_list != -1 and current_selected_algo_idx_in_list < len(self.algo_names_list) - 1:
                            self.selected_algo_name = self.algo_names_list[current_selected_algo_idx_in_list + 1]
                            if current_selected_algo_idx_in_list + 1 >= self.current_algo_scroll_idx + self.num_algos_to_display: self.current_algo_scroll_idx = min(len(self.algo_names_list) - self.num_algos_to_display, current_selected_algo_idx_in_list + 1 - self.num_algos_to_display + 1); self.current_algo_scroll_idx = max(0, self.current_algo_scroll_idx)
                        elif (self.current_algo_scroll_idx + self.num_algos_to_display) < len(self.algo_names_list): self.current_algo_scroll_idx +=1
            if self.fading_in or self.fading_out: continue
            speed_bar_rect = self.speed_slider_elements["bar_rect"]
            if speed_bar_rect.collidepoint(mouse_pos) and mouse_pressed[0]:
                relative_x = mouse_pos[0] - speed_bar_rect.left; progress = max(0, min(1, relative_x / speed_bar_rect.width))
                num_options = len(self.speed_slider_options)
                if num_options > 1: closest_option_idx = min(range(num_options), key=lambda i: abs(i / (num_options - 1) - progress))
                else: closest_option_idx = 0
                if self.current_speed_option_idx != closest_option_idx: self.current_speed_option_idx = closest_option_idx; self.game_speed_multiplier[0] = self.speed_slider_options[self.current_speed_option_idx]; self.controls_status_message = f"Game speed set to: {self.game_speed_multiplier[0]}x"; print(f"Game speed set to: {self.game_speed_multiplier[0]}x")
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.controls_area_rect.collidepoint(mouse_pos):
                    if self.algo_scroll_left_arrow_rect.collidepoint(mouse_pos):
                        if self.current_algo_scroll_idx > 0: self.current_algo_scroll_idx = max(0, self.current_algo_scroll_idx - 1)
                    elif self.algo_scroll_right_arrow_rect.collidepoint(mouse_pos):
                        if (self.current_algo_scroll_idx + self.num_algos_to_display) < len(self.algo_names_list): self.current_algo_scroll_idx = min(len(self.algo_names_list) - self.num_algos_to_display, self.current_algo_scroll_idx + 1)
                    temp_btn_x = self.algo_display_x_start; base_y_algo_btn = self.algo_scroll_left_arrow_rect.y
                    for i in range(self.num_algos_to_display):
                        algo_idx_clicked = self.current_algo_scroll_idx + i
                        if algo_idx_clicked < len(self.algo_names_list):
                            name_clicked = self.algo_names_list[algo_idx_clicked]
                            btn_rect_clicked = pygame.Rect(temp_btn_x, base_y_algo_btn, self.algo_button_width, UI_BUTTON_HEIGHT)
                            if btn_rect_clicked.collidepoint(mouse_pos): self.selected_algo_name = name_clicked; self.controls_status_message = f"Selected: {self.selected_algo_name}. Configure and Start."; break
                            temp_btn_x += self.algo_button_width + UI_ELEMENT_PADDING
                        else: break
                    if self.selected_algo_name != "SPO":
                        if self.key_selector_elements["minus_rect"].collidepoint(mouse_pos): self.num_keys_setting = max(MIN_NUM_KEYS_CONFIG, self.num_keys_setting - 1); self.controls_status_message = f"Keys set to: {self.num_keys_setting}"
                        elif self.key_selector_elements["plus_rect"].collidepoint(mouse_pos): self.num_keys_setting = min(MAX_NUM_KEYS_CONFIG, self.num_keys_setting + 1); self.controls_status_message = f"Keys set to: {self.num_keys_setting}"
                    if self.speed_slider_elements["reset_rect"].collidepoint(mouse_pos): self.current_speed_option_idx = self.speed_slider_options.index(1.0); self.game_speed_multiplier[0] = 1.0; self.controls_status_message = f"Game speed reset to: {self.game_speed_multiplier[0]}x"; print(f"Game speed reset to: {self.game_speed_multiplier[0]}x")
                    if self.regenerate_button["rect"].collidepoint(mouse_pos): self._regenerate_maze_action()
                    elif self.start_run_button["rect"].collidepoint(mouse_pos):
                        if self.maze: self._start_run_action()
                        else: self.controls_status_message = "Regenerate maze first before starting."
                    elif self.compare_button["rect"].collidepoint(mouse_pos):
                        if self.current_maze_run_history: self._initiate_fade_to_state("COMPARING_RESULTS")
                        else: self.controls_status_message = "No runs to compare for the current maze."
            if self.game_state.startswith("OUTCOME_"):
                if event.type == pygame.KEYDOWN and event.key in [pygame.K_RETURN, pygame.K_SPACE]: self._initiate_fade_to_state("IDLE_CONFIG"); self.controls_status_message = "Run finished. Select new mode or regenerate."

    def _update_player_gameplay(self, dt):
        if not self.player or not self.maze: return
        keys_pressed = pygame.key.get_pressed(); self.player.update(keys_pressed, self.maze, dt)
        player_pos = self.player.get_pos()
        if player_pos == self.maze.exit_pos:
            if self.player.get_keys_collected() >= self.current_required_keys:
                time_taken = time.time() - self.player_start_time
                report = {"name": "Player", "path_found": True, "time_taken_seconds": f"{time_taken:.2f}", "steps": self.player.move_count, "cost": "N/A (Player)"}
                self.game_reports.append(report); self._append_report_to_file(report); self.current_maze_run_history.append(report); self._initiate_fade_to_state("OUTCOME_PLAYER_WIN")
            else: self.show_missing_keys_msg = True; needed = self.current_required_keys - self.player.get_keys_collected(); self.missing_keys_msg_text = f"Need {needed} more key{'s' if needed > 1 else ''}!"
        else: self.show_missing_keys_msg = False

    def _update_algorithm_gameplay(self, dt):
        if not self.algorithm_runner or not self.maze: return
        self.algorithm_runner.update(dt)
        if self.algorithm_runner.is_done():
            final_results = self.algorithm_runner.get_final_results()
            if final_results: self.game_reports.append(final_results); self._append_report_to_file(final_results); self.current_maze_run_history.append(final_results)
            if self.algorithm_runner.state == "FINISHED": self._initiate_fade_to_state("OUTCOME_ALGORITHM_WIN")
            else: self._initiate_fade_to_state("OUTCOME_ALGORITHM_FAIL")

    def _update_outcome_screens(self, dt):
        self.outcome_display_timer += dt * self.game_speed_multiplier[0]
        if self.outcome_display_timer >= WIN_DELAY: self._initiate_fade_to_state("IDLE_CONFIG"); self.controls_status_message = "Run finished. Select new mode or regenerate."

    def _main_update_loop(self, dt):
        self._update_fades(dt)
        if self.fading_in or self.fading_out: return
        if self.maze and hasattr(self.maze, 'update'): self.maze.update(dt * self.game_speed_multiplier[0])
        if self.game_state == "PLAYING_PLAYER": self._update_player_gameplay(dt)
        elif self.game_state == "PLAYING_ALGORITHM": self._update_algorithm_gameplay(dt)
        elif self.game_state.startswith("OUTCOME_"): self._update_outcome_screens(dt)

    def _draw_maze_area(self):
        draw_rounded_rect(self.screen, DMG_SECONDARY_BG, self.maze_area_rect.inflate(4,4), UI_ROUND_RECT_RADIUS, 2, DMG_UI_BORDER)
        self.maze_render_surface.fill(DMG_DARK_BG)
        if self.maze:
            self.maze.draw(self.maze_render_surface)
            if self.game_state == "PLAYING_PLAYER" and self.player: self.player.draw(self.maze_render_surface)
            elif self.game_state == "PLAYING_ALGORITHM" and self.algorithm_runner: self.algorithm_runner.draw(self.maze_render_surface)
            if self.game_state == "PLAYING_PLAYER" and self.show_missing_keys_msg:
                exit_center_x_on_maze_surf = self.maze.exit_pos[0] * CELL_SIZE + CELL_SIZE // 2; exit_top_y_on_maze_surf = self.maze.exit_pos[1] * CELL_SIZE
                draw_text(self.maze_render_surface, self.missing_keys_msg_text, self.font_s, MISSING_KEY_TEXT_COLOR, (exit_center_x_on_maze_surf, exit_top_y_on_maze_surf - self.font_s.get_height()), background_color=(*DMG_DARK_BG, 200), padding=5)
        else: draw_text(self.maze_render_surface, "Regenerate Maze to Start", self.font_l, DMG_DIM_TEXT, self.maze_render_surface.get_rect().center)
        self.screen.blit(self.maze_render_surface, self.maze_area_rect.topleft)

    def _draw_info_area(self):
        draw_rounded_rect(self.screen, DMG_PRIMARY_BG, self.info_area_rect, UI_ROUND_RECT_RADIUS, 2, DMG_UI_BORDER)
        current_y = self.info_area_rect.top + UI_PADDING; padding_x = UI_PADDING * 1.5
        title_text = "INFO"
        if self.game_state == "PLAYING_PLAYER" and self.player: title_text = "PLAYER STATS"
        elif self.game_state == "PLAYING_ALGORITHM" and self.algorithm_runner: title_text = f"{self.algorithm_runner.name.upper()} STATS"
        elif self.game_state.startswith("OUTCOME_") : title_text = "LAST RUN RESULT"
        elif self.game_state == "IDLE_CONFIG" and self.maze: title_text = "MAZE CONFIG"
        # Removed COMPARING_RESULTS title from here as it's part of the full screen overlay now
        title_rect = draw_text(self.screen, title_text, self.font_m, DMG_PRIMARY_GREEN, (self.info_area_rect.centerx, current_y + self.font_m.get_height()//2))
        current_y = title_rect.bottom + UI_PADDING
        def draw_info_line(key, value, key_font, val_font, key_color, val_color, y_pos):
            key_surf = key_font.render(key, True, key_color); val_surf = val_font.render(str(value), True, val_color)
            key_rect = self.screen.blit(key_surf, (self.info_area_rect.left + padding_x, y_pos))
            self.screen.blit(val_surf, (key_rect.right + 5, y_pos + (key_rect.height - val_surf.get_height()) // 2 )); return key_rect.height + UI_ELEMENT_PADDING // 2
        if self.game_state == "IDLE_CONFIG":
            current_y += draw_info_line("Mode:", self.selected_algo_name, self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_ACCENT_GREEN, current_y)
            keys_val = self.num_keys_setting if self.selected_algo_name != "SPO" else "0 (SPO)"
            current_y += draw_info_line("Keys Set:", keys_val, self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            current_y += draw_info_line("Speed:", f"{self.game_speed_multiplier[0]:.2f}x", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            if self.maze:
                current_y += UI_PADDING; current_y += draw_info_line("Maze Size:", f"{MAZE_WIDTH}x{MAZE_HEIGHT}", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                current_y += draw_info_line("Keys Req.:", self.current_required_keys, self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                current_y += draw_info_line("Puddles:", getattr(self.maze, 'actual_num_puddles', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                current_y += draw_info_line("Slides:", getattr(self.maze, 'actual_num_slides', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                current_y += draw_info_line("Portals:", f"{getattr(self.maze, 'actual_num_portal_pairs', 'N/A')} pairs", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                current_y += UI_PADDING; current_y += draw_info_line("Runs on Maze:", len(self.current_maze_run_history), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            else: info_sf = self.font_s.render("No maze generated.", True, DMG_DIM_TEXT); self.screen.blit(info_sf, (self.info_area_rect.left + padding_x, current_y)); current_y += info_sf.get_height() + UI_ELEMENT_PADDING
        elif self.game_state == "PLAYING_PLAYER" and self.player and self.maze:
            current_y += draw_info_line("Keys:", f"{self.player.get_keys_collected()} / {self.current_required_keys}", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_ACCENT_GREEN, current_y)
            current_y += draw_info_line("Moves:", self.player.move_count, self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            time_elapsed = time.time() - self.player_start_time; current_y += draw_info_line("Time:", f"{time_elapsed:.1f}s", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            current_y += draw_info_line("Speed:", f"{self.game_speed_multiplier[0]:.2f}x", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
        elif self.game_state == "PLAYING_ALGORITHM" and self.algorithm_runner:
            status_text_sf = self.font_s.render(self.algorithm_runner.get_status_text(), True, DMG_LIGHT_TEXT); self.screen.blit(status_text_sf, (self.info_area_rect.left + padding_x, current_y)); current_y += status_text_sf.get_height() + UI_PADDING
            if self.algorithm_runner.results:
                res = self.algorithm_runner.results; found_color = DMG_ACCENT_GREEN if res.get('path_found') else DMG_WARN_TEXT
                current_y += draw_info_line("Path Found:", "Yes" if res.get('path_found') else "No", self.font_s, self.font_s, DMG_LIGHT_TEXT, found_color, current_y)
                if res.get('path_found'): current_y += draw_info_line("Cost:", res.get('cost', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y); current_y += draw_info_line("Steps:", res.get('steps', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            current_y += draw_info_line("Speed:", f"{self.game_speed_multiplier[0]:.2f}x", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
        elif self.game_state.startswith("OUTCOME_") :
            report_to_show = None
            if self.current_maze_run_history : report_to_show = self.current_maze_run_history[-1]
            elif self.game_reports : report_to_show = self.game_reports[-1]
            if report_to_show:
                current_y += draw_info_line("Mode:", report_to_show.get('name', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_ACCENT_GREEN, current_y)
                if report_to_show.get('name', '').lower() == "player": current_y += draw_info_line("Time:", f"{report_to_show.get('time_taken_seconds', 'N/A')}s", self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y); current_y += draw_info_line("Steps:", report_to_show.get('steps', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                else:
                    found_color = DMG_ACCENT_GREEN if report_to_show.get('path_found') else DMG_WARN_TEXT
                    current_y += draw_info_line("Path Found:", "Yes" if report_to_show.get('path_found') else "No", self.font_s, self.font_s, DMG_LIGHT_TEXT, found_color, current_y)
                    if report_to_show.get('path_found'): current_y += draw_info_line("Cost:", report_to_show.get('cost', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y); current_y += draw_info_line("Steps:", report_to_show.get('steps', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
                    current_y += draw_info_line("Nodes:", report_to_show.get('nodes_expanded', 'N/A'), self.font_s, self.font_s, DMG_LIGHT_TEXT, DMG_LIGHT_TEXT, current_y)
            else: info_sf = self.font_s.render("No report data.", True, DMG_DIM_TEXT); self.screen.blit(info_sf, (self.info_area_rect.left + padding_x, current_y)); current_y += info_sf.get_height() + UI_ELEMENT_PADDING
        # Removed the COMPARING_RESULTS block from here as it's now handled by the full-screen overlay
        if self.game_state == "PLAYING_ALGORITHM" and self.algorithm_runner and isinstance(self.algorithm_runner.solver, SPOSolver) and hasattr(self.algorithm_runner.solver, 'draw_belief_map'):
            map_title_sf = self.font_s.render("SPO Belief Map:", True, DMG_PRIMARY_GREEN); map_title_rect = self.screen.blit(map_title_sf, (self.info_area_rect.left + padding_x, current_y)); current_y = map_title_rect.bottom + UI_ELEMENT_PADDING // 2
            belief_map_available_height = self.info_area_rect.bottom - current_y - UI_PADDING
            if self.maze and belief_map_available_height > 50 :
                max_map_width = self.info_area_rect.width - 2 * padding_x; belief_cell_size = min(max_map_width // self.maze.width, belief_map_available_height // self.maze.height); belief_cell_size = max(1, belief_cell_size)
                belief_map_width = self.maze.width * belief_cell_size; belief_map_height = self.maze.height * belief_cell_size
                belief_map_x = self.info_area_rect.left + (self.info_area_rect.width - belief_map_width) // 2; belief_map_y = current_y
                if belief_map_width > 0 and belief_map_height > 0: temp_belief_surface = pygame.Surface((belief_map_width, belief_map_height)); self.algorithm_runner.solver.draw_belief_map(temp_belief_surface, belief_cell_size); self.screen.blit(temp_belief_surface, (belief_map_x, belief_map_y))

    def _draw_controls_area(self):
        draw_rounded_rect(self.screen, DMG_SECONDARY_BG, self.controls_area_rect, UI_ROUND_RECT_RADIUS, 2, DMG_UI_BORDER); mouse_pos = pygame.mouse.get_pos()
        label_y_offset_algo = self.algo_section_label_pos[1]; label_y_offset_config = self.config_section_label_pos[1]; label_y_offset_action = self.action_section_label_pos[1]
        self.screen.blit(self.algo_section_label["font"].render(self.algo_section_label["text"], True, self.algo_section_label["color"]), (self.algo_section_label_pos[0], label_y_offset_algo))
        self.screen.blit(self.config_section_label["font"].render(self.config_section_label["text"], True, self.config_section_label["color"]), (self.config_section_label_pos[0], label_y_offset_config))
        self.screen.blit(self.action_section_label["font"].render(self.action_section_label["text"], True, self.action_section_label["color"]), (self.action_section_label_pos[0], label_y_offset_action))
        base_y_algo = self.algo_scroll_left_arrow_rect.y; arrow_color_active = DMG_LIGHT_TEXT; arrow_color_inactive = DMG_DIM_TEXT
        can_scroll_left = self.current_algo_scroll_idx > 0
        draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if self.algo_scroll_left_arrow_rect.collidepoint(mouse_pos) and can_scroll_left else DMG_UI_BUTTON, self.algo_scroll_left_arrow_rect, UI_ROUND_RECT_RADIUS // 2, 0)
        pygame.draw.polygon(self.screen, arrow_color_active if can_scroll_left else arrow_color_inactive, [(self.algo_scroll_left_arrow_rect.centerx + 3, self.algo_scroll_left_arrow_rect.centery), (self.algo_scroll_left_arrow_rect.centerx - 3, self.algo_scroll_left_arrow_rect.top + 7), (self.algo_scroll_left_arrow_rect.centerx - 3, self.algo_scroll_left_arrow_rect.bottom - 7)])
        current_btn_x = self.algo_display_x_start
        for i in range(self.num_algos_to_display):
            algo_idx_to_draw = self.current_algo_scroll_idx + i
            if algo_idx_to_draw < len(self.algo_names_list):
                name = self.algo_names_list[algo_idx_to_draw]; btn_rect = pygame.Rect(current_btn_x, base_y_algo, self.algo_button_width, UI_BUTTON_HEIGHT)
                is_selected = (name == self.selected_algo_name); is_hovered = btn_rect.collidepoint(mouse_pos)
                bg_color = DMG_UI_BUTTON_ACTIVE if is_selected else (DMG_UI_BUTTON_HOVER if is_hovered else DMG_UI_BUTTON); border_thick = 2 if is_selected else 1; border_color = DMG_ACCENT_GREEN if is_selected else (DMG_HOVER_GREEN if is_hovered else DMG_UI_BORDER)
                draw_rounded_rect(self.screen, bg_color, btn_rect, UI_ROUND_RECT_RADIUS, border_thick, border_color); font_to_use = self.font_s; draw_text(self.screen, name, font_to_use, DMG_UI_BUTTON_TEXT, btn_rect.center)
                current_btn_x += self.algo_button_width + UI_ELEMENT_PADDING
            else: break
        can_scroll_right = (self.current_algo_scroll_idx + self.num_algos_to_display) < len(self.algo_names_list)
        draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if self.algo_scroll_right_arrow_rect.collidepoint(mouse_pos) and can_scroll_right else DMG_UI_BUTTON, self.algo_scroll_right_arrow_rect, UI_ROUND_RECT_RADIUS // 2, 0)
        pygame.draw.polygon(self.screen, arrow_color_active if can_scroll_right else arrow_color_inactive, [(self.algo_scroll_right_arrow_rect.centerx - 3, self.algo_scroll_right_arrow_rect.centery), (self.algo_scroll_right_arrow_rect.centerx + 3, self.algo_scroll_right_arrow_rect.top + 7), (self.algo_scroll_right_arrow_rect.centerx + 3, self.algo_scroll_right_arrow_rect.bottom - 7)])
        self.screen.blit(self.key_selector_elements["label_surf"], self.key_selector_elements["label_rect"]); is_spo_selected = (self.selected_algo_name == "SPO")
        minus_rect = self.key_selector_elements["minus_rect"]; is_hovered_minus = minus_rect.collidepoint(mouse_pos) and not is_spo_selected
        draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if is_hovered_minus else DMG_UI_BUTTON, minus_rect, UI_ROUND_RECT_RADIUS//3, 0); draw_text(self.screen, "-", self.font_m, DMG_LIGHT_TEXT if not is_spo_selected else DMG_DIM_TEXT, minus_rect.center)
        display_rect = self.key_selector_elements["display_rect"]; draw_rounded_rect(self.screen, DMG_INPUT_BG, display_rect, UI_ROUND_RECT_RADIUS//2, 1, DMG_INPUT_BORDER); keys_val_text = str(self.num_keys_setting if not is_spo_selected else 0); draw_text(self.screen, keys_val_text, self.font_m, DMG_LIGHT_TEXT, display_rect.center)
        plus_rect = self.key_selector_elements["plus_rect"]; is_hovered_plus = plus_rect.collidepoint(mouse_pos) and not is_spo_selected
        draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if is_hovered_plus else DMG_UI_BUTTON, plus_rect, UI_ROUND_RECT_RADIUS//3, 0); draw_text(self.screen, "+", self.font_m, DMG_LIGHT_TEXT if not is_spo_selected else DMG_DIM_TEXT, plus_rect.center)
        self.screen.blit(self.speed_slider_elements["label_surf"], self.speed_slider_elements["label_rect"]); bar_rect = self.speed_slider_elements["bar_rect"]; pygame.draw.rect(self.screen, DMG_SLIDER_TRACK_COLOR, bar_rect, 0, UI_ROUND_RECT_RADIUS // 3)
        num_speed_options = len(self.speed_slider_options)
        if num_speed_options > 1:
            for i in range(num_speed_options): tick_x = bar_rect.left + int((i / (num_speed_options - 1)) * bar_rect.width); tick_y_start = bar_rect.centery - UI_SLIDER_TRACK_HEIGHT // 2; tick_y_end = bar_rect.centery + UI_SLIDER_TRACK_HEIGHT // 2; pygame.draw.line(self.screen, DMG_SECONDARY_BG, (tick_x, tick_y_start), (tick_x, tick_y_end), 1)
        knob_x_progress = 0.5
        if num_speed_options > 1: knob_x_progress = self.current_speed_option_idx / (num_speed_options - 1)
        knob_center_x = bar_rect.left + int(knob_x_progress * bar_rect.width); pygame.draw.circle(self.screen, DMG_SLIDER_KNOB_COLOR, (knob_center_x, bar_rect.centery), self.speed_slider_elements["knob_radius"]); pygame.draw.circle(self.screen, DMG_SLIDER_KNOB_OUTLINE, (knob_center_x, bar_rect.centery), self.speed_slider_elements["knob_radius"] -1, 1)
        speed_val_text = f"{self.game_speed_multiplier[0]:.2f}x"; speed_val_text_size = self.font_xs.size(speed_val_text); draw_text(self.screen, speed_val_text, self.font_xs, DMG_LIGHT_TEXT, (self.speed_slider_elements["value_text_pos_x"] + speed_val_text_size[0]//2, bar_rect.centery))
        reset_rect_speed = self.speed_slider_elements["reset_rect"]; is_hovered_reset_speed = reset_rect_speed.collidepoint(mouse_pos); draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if is_hovered_reset_speed else DMG_UI_BUTTON, reset_rect_speed, UI_ROUND_RECT_RADIUS // 3, 0)
        pygame.draw.arc(self.screen, DMG_LIGHT_TEXT, reset_rect_speed.inflate(-reset_rect_speed.width//3, -reset_rect_speed.height//3), math.radians(90), math.radians(360), 2); pygame.draw.polygon(self.screen, DMG_LIGHT_TEXT, [(reset_rect_speed.centerx, reset_rect_speed.top + reset_rect_speed.height//4), (reset_rect_speed.centerx - reset_rect_speed.width//6, reset_rect_speed.top + reset_rect_speed.height//2.5), (reset_rect_speed.centerx + reset_rect_speed.width//6, reset_rect_speed.top + reset_rect_speed.height//2.5),])
        regen_rect = self.regenerate_button["rect"]; is_hovered_regen = regen_rect.collidepoint(mouse_pos); draw_rounded_rect(self.screen, DMG_UI_BUTTON_HOVER if is_hovered_regen else DMG_UI_BUTTON, regen_rect, UI_ROUND_RECT_RADIUS, 1, DMG_UI_BORDER if not is_hovered_regen else DMG_HOVER_GREEN); draw_text(self.screen, self.regenerate_button["text"], self.font_m, DMG_UI_BUTTON_TEXT, regen_rect.center)
        start_rect = self.start_run_button["rect"]; is_hovered_start = start_rect.collidepoint(mouse_pos); can_start = bool(self.maze); start_bg = DMG_PRIMARY_GREEN if can_start else DMG_UI_BUTTON_DISABLED_BG; start_txt_color = DMG_DARK_BG if can_start else DMG_UI_BUTTON_DISABLED_TEXT; start_border = DMG_ACCENT_GREEN if can_start else DMG_UI_BORDER
        if can_start and is_hovered_start: start_bg = DMG_HOVER_GREEN
        elif not can_start and is_hovered_start : start_bg = DMG_UI_BUTTON_DISABLED_BG
        draw_rounded_rect(self.screen, start_bg, start_rect, UI_ROUND_RECT_RADIUS, 2, start_border); draw_text(self.screen, self.start_run_button["text"], self.font_m, start_txt_color, start_rect.center)
        compare_rect = self.compare_button["rect"]; is_hovered_compare = compare_rect.collidepoint(mouse_pos); can_compare = bool(self.current_maze_run_history); compare_bg = DMG_UI_BUTTON; compare_txt = DMG_UI_BUTTON_DISABLED_TEXT; compare_border = DMG_UI_BORDER
        if can_compare: compare_bg = DMG_UI_BUTTON_HOVER if is_hovered_compare else DMG_UI_BUTTON; compare_txt = DMG_UI_BUTTON_TEXT; compare_border = DMG_HOVER_GREEN if is_hovered_compare else DMG_UI_BORDER
        draw_rounded_rect(self.screen, compare_bg, compare_rect, UI_ROUND_RECT_RADIUS, 1, compare_border); draw_text(self.screen, self.compare_button["text"], self.font_m, compare_txt, compare_rect.center)
        draw_text(self.screen, self.controls_status_message, self.font_xs, DMG_DIM_TEXT, self.controls_status_rect.center, background_color=DMG_PANEL_SECTION_BG, padding=UI_ELEMENT_PADDING//2)
    
    def _draw_compare_results_screen(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*DMG_DARK_BG, 245)) 
        self.screen.blit(overlay, (0,0))

        title_rect = draw_text(self.screen, "Run Comparison", self.font_xl, DMG_PRIMARY_GREEN, 
                               (self.screen.get_width() // 2, UI_PADDING * 3))

        if not self.current_maze_run_history:
            draw_text(self.screen, "No run data available for this maze.", self.font_l, DMG_DIM_TEXT, 
                      self.screen.get_rect().center)
            draw_text(self.screen, "Press ESC or ENTER to Continue", self.font_s, DMG_DIM_TEXT, 
                      (self.screen.get_width()//2, self.screen.get_height() - UI_PADDING * 2))
            return

        content_y_start = title_rect.bottom + UI_PADDING * 2
        available_width_for_content = self.screen.get_width() * 0.92 
        content_x_offset = (self.screen.get_width() - available_width_for_content) / 2

        table_width_ratio = 0.65 
        summary_width_ratio = 0.32 
        gap_width_ratio = 1.0 - table_width_ratio - summary_width_ratio 

        table_width_abs = available_width_for_content * table_width_ratio
        summary_width_abs = available_width_for_content * summary_width_ratio
        gap_abs = available_width_for_content * gap_width_ratio

        table_x_start_abs = content_x_offset
        summary_x_start_abs = table_x_start_abs + table_width_abs + gap_abs
        
        col_headers = ["Algorithm", "Path?", "Cost/Time", "Steps", "Nodes"]
        col_prop_original = [0.3, 0.1, 0.2, 0.15, 0.15] 
        sum_original_col_prop = sum(col_prop_original)
        if sum_original_col_prop == 0: sum_original_col_prop = 1 

        col_widths = [int(table_width_abs * (p / sum_original_col_prop)) for p in col_prop_original]
        
        width_diff = int(table_width_abs - sum(col_widths)) 
        if col_widths: 
            for i in range(abs(width_diff)): 
                idx_adjust = i % len(col_widths)
                col_widths[idx_adjust] += 1 if width_diff > 0 else -1
        
        current_y_table_draw = content_y_start
        header_height = self.font_m.get_height() + UI_PADDING
        row_height = self.font_s.get_height() + UI_PADDING // 2
        
        current_x_col_header = table_x_start_abs
        for i, header in enumerate(col_headers):
            header_cell_rect = pygame.Rect(current_x_col_header, current_y_table_draw, col_widths[i], header_height)
            draw_text(self.screen, header, self.font_m, DMG_ACCENT_GREEN, header_cell_rect.center)
            current_x_col_header += col_widths[i]
        
        current_y_table_draw += header_height + UI_ELEMENT_PADDING // 2
        
        max_table_y_draw = self.screen.get_height() - UI_PADDING * 4 
        rows_drawn_count = 0
        for idx, run_data in enumerate(self.current_maze_run_history):
            if current_y_table_draw + row_height > max_table_y_draw and rows_drawn_count > 0:
                draw_text(self.screen, "...", self.font_s, DMG_DIM_TEXT, 
                          (table_x_start_abs + table_width_abs / 2, current_y_table_draw + row_height / 2))
                break

            row_bg_color = DMG_PRIMARY_BG if idx % 2 == 0 else DMG_PANEL_SECTION_BG
            cost_time_val = "-"
            if run_data.get('name','').lower() == "player": 
                cost_time_val = f"{run_data.get('time_taken_seconds','-')}s"
            elif run_data.get('path_found'): 
                cost_time_val = str(run_data.get('cost', '-'))
            
            row_values = [
                run_data.get('name', 'N/A'), 
                "Yes" if run_data.get('path_found') else "No", 
                cost_time_val, 
                str(run_data.get('steps', '-')) if (run_data.get('path_found') or run_data.get('name','').lower() == "player") else "-", 
                str(run_data.get('nodes_expanded', '-')) if run_data.get('name','').lower() != "player" else "-"
            ]
            
            current_x_col_row = table_x_start_abs
            row_base_rect = pygame.Rect(table_x_start_abs, current_y_table_draw, table_width_abs, row_height)
            draw_rounded_rect(self.screen, row_bg_color, row_base_rect, UI_ROUND_RECT_RADIUS//3)

            for i, value in enumerate(row_values):
                cell_rect = pygame.Rect(current_x_col_row, current_y_table_draw, col_widths[i], row_height)
                text_color = DMG_WARN_TEXT if value == "No" and i == 1 else DMG_LIGHT_TEXT
                font_to_use = self.font_s
                align_center_x = cell_rect.centerx
                if i == 0: 
                    align_center_x = cell_rect.left + UI_PADDING
                    text_surf = font_to_use.render(value, True, text_color)
                    self.screen.blit(text_surf, text_surf.get_rect(midleft=(align_center_x, cell_rect.centery)))
                else:
                    draw_text(self.screen, value, font_to_use, text_color, cell_rect.center)
                current_x_col_row += col_widths[i]
            
            current_y_table_draw += row_height + UI_ELEMENT_PADDING // 3
            rows_drawn_count +=1

        algo_runs = [run for run in self.current_maze_run_history if run.get('name', '').lower() != 'player']
        successful_algo_runs = [run for run in algo_runs if run.get('path_found')]

        path_finder_names = sorted(list(set(run.get('name') for run in successful_algo_runs if run.get('name'))))
        best_path_text = ", ".join(path_finder_names) if path_finder_names else "None"

        min_cost_val = float('inf')
        best_cost_algo_names_raw = []
        if successful_algo_runs:
            for run in successful_algo_runs:
                cost_val_from_run = run.get('cost')
                current_run_cost = float('inf')
                if isinstance(cost_val_from_run, (int, float)): 
                    current_run_cost = float(cost_val_from_run)
                elif isinstance(cost_val_from_run, str):
                    try: current_run_cost = float(cost_val_from_run)
                    except ValueError: pass 
                
                if current_run_cost < min_cost_val:
                    min_cost_val = current_run_cost
                    best_cost_algo_names_raw = [run.get('name')]
                elif current_run_cost == min_cost_val and run.get('name') and run.get('name') not in best_cost_algo_names_raw :
                    best_cost_algo_names_raw.append(run.get('name'))
        
        best_cost_algo_names = sorted(list(set(name for name in best_cost_algo_names_raw if name)))
        if best_cost_algo_names:
            cost_display_val = f"({min_cost_val:.0f})" if min_cost_val != float('inf') else ""
            best_cost_text = f"{', '.join(best_cost_algo_names)} {cost_display_val}".strip()
        else:
            best_cost_text = "N/A"

        min_steps_val = float('inf')
        best_steps_algo_names_raw = []
        if successful_algo_runs:
            for run in successful_algo_runs:
                steps_val_from_run = run.get('steps')
                current_run_steps = float('inf')
                if isinstance(steps_val_from_run, (int, float)): 
                    current_run_steps = int(steps_val_from_run)
                elif isinstance(steps_val_from_run, str):
                    try: current_run_steps = int(steps_val_from_run)
                    except ValueError: pass

                if current_run_steps < min_steps_val:
                    min_steps_val = current_run_steps
                    best_steps_algo_names_raw = [run.get('name')]
                elif current_run_steps == min_steps_val and run.get('name') and run.get('name') not in best_steps_algo_names_raw:
                    best_steps_algo_names_raw.append(run.get('name'))

        best_steps_algo_names = sorted(list(set(name for name in best_steps_algo_names_raw if name)))
        if best_steps_algo_names:
            steps_display_val = f"({min_steps_val})" if min_steps_val != float('inf') else ""
            best_steps_text = f"{', '.join(best_steps_algo_names)} {steps_display_val}".strip()
        else:
            best_steps_text = "N/A"

        summary_y_current_draw = content_y_start
        summary_padding_horiz_val = UI_PADDING
        summary_item_spacing_vert = UI_ELEMENT_PADDING 
        
        summary_panel_title_font = self.font_m
        summary_line_font = self.font_s
        summary_label_color_val = DMG_PRIMARY_GREEN 
        summary_value_color_val = DMG_LIGHT_TEXT

        panel_title_text = "Optimal Performers"
        panel_title_surf = summary_panel_title_font.render(panel_title_text, True, DMG_PRIMARY_GREEN)
        panel_title_rect = panel_title_surf.get_rect(midtop=(summary_x_start_abs + summary_width_abs / 2, summary_y_current_draw))
        self.screen.blit(panel_title_surf, panel_title_rect)
        summary_y_current_draw = panel_title_rect.bottom + UI_PADDING

        summary_items_to_draw = [
            ("Path Found By:", best_path_text),
            ("Lowest Cost:", best_cost_text),
            ("Fewest Steps:", best_steps_text),
        ]
        
        for label_str, value_str in summary_items_to_draw:
            label_surface = summary_line_font.render(label_str, True, summary_label_color_val)
            label_draw_rect = label_surface.get_rect(topleft=(summary_x_start_abs + summary_padding_horiz_val, summary_y_current_draw))
            self.screen.blit(label_surface, label_draw_rect)
            summary_y_current_draw += label_surface.get_height() * 0.9 

            value_surface = summary_line_font.render(value_str, True, summary_value_color_val)
            max_value_width = summary_width_abs - (summary_padding_horiz_val * 2) - 15 
            
            if value_surface.get_width() > max_value_width:
                words = value_str.split(' ') 
                current_line_text = ""
                lines_to_render = []
                for word in words:
                    test_line = current_line_text + (" " if current_line_text else "") + word
                    if summary_line_font.size(test_line)[0] <= max_value_width:
                        current_line_text = test_line
                    else:
                        if current_line_text: lines_to_render.append(current_line_text)
                        current_line_text = word 
                if current_line_text: lines_to_render.append(current_line_text)

                for i, line_text_to_render in enumerate(lines_to_render):
                    line_surf = summary_line_font.render(line_text_to_render, True, summary_value_color_val)
                    indent_val = summary_padding_horiz_val + 15
                    self.screen.blit(line_surf, (summary_x_start_abs + indent_val, summary_y_current_draw))
                    summary_y_current_draw += line_surf.get_height() * 0.95 
            else:
                value_draw_rect = value_surface.get_rect(topleft=(summary_x_start_abs + summary_padding_horiz_val + 15, summary_y_current_draw))
                self.screen.blit(value_surface, value_draw_rect)
                summary_y_current_draw += value_surface.get_height()
            summary_y_current_draw += summary_item_spacing_vert * 1.8 

        draw_text(self.screen, "Press ESC or ENTER to Continue", self.font_s, DMG_DIM_TEXT, 
                  (self.screen.get_width()//2, self.screen.get_height() - UI_PADDING * 2))


    def _draw_outcome_screen(self, title_text, title_color=DMG_PRIMARY_GREEN):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA); overlay.fill((*DMG_DARK_BG, 240)); self.screen.blit(overlay, (0,0)); img_y_offset = 0
        if self.game_state == "OUTCOME_PLAYER_WIN" and self.player and hasattr(self.player, 'win_image') and self.player.win_image:
            win_img_rect = self.player.win_image.get_rect(centerx=self.screen.get_width() // 2, top=self.screen.get_height() * 0.15); self.screen.blit(self.player.win_image, win_img_rect); img_y_offset = win_img_rect.bottom + UI_PADDING * 2
        else: img_y_offset = self.screen.get_height() * 0.25
        title_rect = draw_text(self.screen, title_text, self.font_xl, title_color, (self.screen.get_width() // 2, img_y_offset)); report_to_show = None
        if self.current_maze_run_history : report_to_show = self.current_maze_run_history[-1]
        elif self.game_reports : report_to_show = self.game_reports[-1]
        current_y_report = title_rect.bottom + UI_PADDING * 2.5
        if report_to_show:
            lines = []; lines.append((f"Mode:", report_to_show.get('name', 'N/A'), DMG_ACCENT_GREEN))
            if report_to_show.get('name', '').lower() == "player": lines.append((f"Time:", f"{report_to_show.get('time_taken_seconds', 'N/A')}s", DMG_LIGHT_TEXT)); lines.append((f"Steps:", report_to_show.get('steps', 'N/A'), DMG_LIGHT_TEXT))
            else:
                found_color = DMG_ACCENT_GREEN if report_to_show.get('path_found') else DMG_WARN_TEXT; lines.append((f"Path Found:", "Yes" if report_to_show.get('path_found') else "No", found_color))
                if report_to_show.get('path_found'): lines.append((f"Cost:", report_to_show.get('cost', 'N/A'), DMG_LIGHT_TEXT)); lines.append((f"Steps:", report_to_show.get('steps', 'N/A'), DMG_LIGHT_TEXT))
                lines.append((f"Nodes Explored:", report_to_show.get('nodes_expanded', 'N/A'), DMG_LIGHT_TEXT))
            for key_text, val_text, val_color in lines:
                key_surf = self.font_m.render(key_text, True, DMG_LIGHT_TEXT); val_surf = self.font_m.render(str(val_text), True, val_color); total_width = key_surf.get_width() + val_surf.get_width() + UI_ELEMENT_PADDING; start_x = (self.screen.get_width() - total_width) // 2
                self.screen.blit(key_surf, (start_x, current_y_report)); self.screen.blit(val_surf, (start_x + key_surf.get_width() + UI_ELEMENT_PADDING, current_y_report)); current_y_report += self.font_m.get_height() + UI_ELEMENT_PADDING // 2
        draw_text(self.screen, "Press ENTER or SPACE to Continue", self.font_s, DMG_DIM_TEXT, (self.screen.get_width()//2, self.screen.get_height() - UI_PADDING * 3))

    def _main_draw_call(self):
        self.screen.fill(DMG_DARK_BG)
        if self.game_state != "COMPARING_RESULTS":
            self._draw_maze_area()
            self._draw_info_area()
            self._draw_controls_area()

        if self.game_state == "COMPARING_RESULTS": 
            self._draw_compare_results_screen()
        elif self.game_state == "OUTCOME_PLAYER_WIN": 
            self._draw_outcome_screen("Player Escaped!", DMG_ACCENT_GREEN)
        elif self.game_state == "OUTCOME_ALGORITHM_WIN": 
            algo_name_disp = self.algorithm_runner.name if self.algorithm_runner else 'Algorithm'
            self._draw_outcome_screen(f"{algo_name_disp} Found Exit!", DMG_ACCENT_GREEN)
        elif self.game_state == "OUTCOME_ALGORITHM_FAIL": 
            algo_name_disp = self.algorithm_runner.name if self.algorithm_runner else 'Algorithm'
            self._draw_outcome_screen(f"{algo_name_disp} Failed!", DMG_WARN_TEXT)
        
        if self.fading_out or self.fading_in: 
            self.transition_surface.set_alpha(self.transition_alpha)
            self.screen.blit(self.transition_surface, (0,0))
        
        pygame.display.flip()

    def _append_report_to_file(self, report_data_dict):
        if not report_data_dict: return
        try:
            with open(REPORT_FILENAME, "a", encoding="utf-8") as f:
                f.write(f"\n--- Run @ {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"); keys_set = self.num_keys_setting if report_data_dict.get('name') != "SPO" else 0
                f.write(f"Maze: {MAZE_WIDTH}x{MAZE_HEIGHT}, Keys Set: {keys_set}, Actual Keys Req: {self.current_required_keys}, Speed: {self.game_speed_multiplier[0]:.2f}x\n")
                name = report_data_dict.get('name', 'N/A'); f.write(f"  Mode: {name}\n")
                if name.lower() == "player": f.write(f"    Time: {report_data_dict.get('time_taken_seconds', 'N/A')}s\n    Steps: {report_data_dict.get('steps', 'N/A')}\n")
                else:
                    found = 'Yes' if report_data_dict.get('path_found') else 'No'; f.write(f"    Path Found: {found}\n")
                    if report_data_dict.get('path_found'): f.write(f"    Path Cost: {report_data_dict.get('cost', 'N/A')}\n    Path Steps: {report_data_dict.get('steps', 'N/A')}\n")
                    f.write(f"    Nodes Expanded: {report_data_dict.get('nodes_expanded', 'N/A')}\n")
                f.write(f"--- End Run Entry ---\n")
        except Exception as e: print(f"Error writing report: {e}", file=sys.stderr); traceback.print_exc()

    def run(self):
        if self.game_state == "IDLE_CONFIG" and not self.maze:
            self._regenerate_maze_action() 
        
        self._manage_music_transition(self.game_state, None)

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_input()
            self._main_update_loop(dt)
            self._main_draw_call()
            
        print("Exiting game gracefully...");
        if pygame.mixer.get_init():
            pygame.mixer.music.stop() #
            pygame.mixer.quit()
        pygame.quit()
        sys.exit()