import pygame

# --- Screen & Maze Dimensions ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

CONTROLS_AREA_HEIGHT = 130 # Tăng nhẹ chiều cao cho controls
INFO_AREA_WIDTH = 320    # Tăng nhẹ chiều rộng cho info
MAZE_AREA_WIDTH = SCREEN_WIDTH - INFO_AREA_WIDTH
MAZE_AREA_HEIGHT = SCREEN_HEIGHT - CONTROLS_AREA_HEIGHT

CELL_SIZE = 28
MAZE_WIDTH = MAZE_AREA_WIDTH // CELL_SIZE - 1
MAZE_HEIGHT = MAZE_AREA_HEIGHT // CELL_SIZE 


# --- Dark Modern Green Theme Colors ---
DMG_DARK_BG = (18, 22, 20)          # Main background
DMG_PRIMARY_BG = (25, 35, 30)       # Info panel background
DMG_SECONDARY_BG = (35, 50, 45)     # Controls panel background
DMG_PANEL_SECTION_BG = (40, 55, 50) # Slightly lighter for sections within controls

DMG_PRIMARY_GREEN = (0, 204, 102)   # Bright green for primary actions, highlights
DMG_ACCENT_GREEN = (10, 230, 130)   # Slightly brighter green for accents
DMG_HOVER_GREEN = (50, 220, 150)    # Hover for primary green elements

DMG_LIGHT_TEXT = (210, 230, 220)    # Main text color
DMG_DIM_TEXT = (140, 160, 150)      # For less important text, disabled states
DMG_WARN_TEXT = (255, 100, 100)     # For warnings, errors

DMG_UI_BORDER = (0, 150, 90)        # Borders for panels, some UI elements
DMG_UI_BUTTON = (45, 70, 60)        # Default button background
DMG_UI_BUTTON_HOVER = (60, 90, 80)  # Default button hover
DMG_UI_BUTTON_ACTIVE = DMG_PRIMARY_GREEN # Selected/Active button background (e.g., algo selector)
DMG_UI_BUTTON_TEXT = DMG_LIGHT_TEXT
DMG_UI_BUTTON_DISABLED_BG = (40, 50, 45)
DMG_UI_BUTTON_DISABLED_TEXT = (100, 110, 105)

DMG_INPUT_BG = (22, 30, 26)         # Background for input-like fields (key count display)
DMG_INPUT_BORDER = (50, 65, 60)

WALL_COLOR = (10, 18, 15)           # Darker than main bg for contrast
PATH_COLOR = (45, 60, 55)           # Path color, distinct from wall
EXIT_COLOR = DMG_PRIMARY_GREEN
KEY_COLOR = DMG_ACCENT_GREEN
MUD_COLOR = (60, 50, 40)
WATER_COLOR = (40, 110, 130)
PORTAL_COLORS_FALLBACK = [
    (0, 200, 200), (0, 170, 230), (20, 150, 210),
    (0, 230, 170), (20, 210, 150), (40, 190, 190)
]
HIGHLIGHT_COLOR = (*DMG_ACCENT_GREEN, 150) # For temporary highlights, RGBA
FALLBACK_IMAGE_COLOR = (255, 0, 255)  # Magenta for missing/failed image loads
MISSING_KEY_TEXT_COLOR = DMG_WARN_TEXT


# --- Player Settings ---
PLAYER_MOVE_SPEED = 0.09
PLAYER_ANIMATION_SPEED = 0.08
PLAYER_MUD_MULTIPLIER = 5

# --- Maze Settings ---
MAZE_LOOP_CHANCE = 0.15
DEFAULT_NUM_KEYS = 0
MIN_NUM_KEYS_CONFIG = 0
MAX_NUM_KEYS_CONFIG = 5
MAX_PORTAL_PAIRS = MAX_NUM_KEYS_CONFIG // 2 if MAX_NUM_KEYS_CONFIG > 0 else 0 # Max 2 pairs if 5 keys
PORTAL_ANIMATION_SPEED = 0.1
MAX_PORTAL_ANIMATION_FRAMES = 5

# --- Mud Puddle Settings ---
BASE_PUDDLES = 2
PUDDLES_PER_KEY_INCREASE = 1
MAX_PUDDLE_DENSITY = 0.08

# --- Water Slide Settings ---
BASE_SLIDES = 1
SLIDES_PER_KEY_INCREASE = 1
MAX_SLIDE_DENSITY = 0.05
MIN_SLIDE_LENGTH = 3
MAX_SLIDE_LENGTH = 5

# --- Costs for Algorithms ---
MUD_COST_ALGO = 5
PORTAL_COST_ALGO = 1
SLIDE_CELL_COST_ALGO = 1

# --- Algorithm Settings ---
ALGORITHM_THINK_TIME_PER_NODE = 0.001 # Time per node for "thinking" phase visualization
ALGORITHM_MOVE_SPEED = PLAYER_MOVE_SPEED # Algorithm "player" moves at same base speed

# --- Algorithm Visualization Colors (Themed RGBA for transparency) ---
VISITED_NODE_COLOR_ALGO = (70, 90, 85, 100)
FRONTIER_NODE_COLOR_ALGO = (60, 130, 150, 90)
FINAL_PATH_COLOR_ALGO = (*DMG_PRIMARY_GREEN, 220) # Brighter and more opaque for final path
NO_PATH_FOUND_COLOR = (*DMG_WARN_TEXT, 200)

# --- Game Settings ---
FPS = 60
WIN_DELAY = 2.5 # Seconds before returning to config from outcome screen
FADE_SPEED = 10 # Alpha change per frame for screen transitions

# --- Asset Paths ---
IMAGE_FOLDER = "images"
SOUNDS_FOLDER = "sounds"
PLAYER_IDLE_IMAGE = "player_idle.png"
PLAYER_WIN_IMAGE = "player_win.png"
PLAYER_WALK_PREFIX = "player_walk_"
EXIT_IMAGE_FILENAME = "exit.png"
KEY_IMAGE_FILENAME = "key.png"
MUD_IMAGE_FILENAME = "mud.png"
WATER_IMAGE_FILENAME = "water.png"
PORTAL_IMAGE_PREFIX = "portal_"
PATH_IMAGE_FILENAME = "path.png"

# --- Sound Asset Filenames ---
KEY_PICKUP_SOUND = "key_pickup.wav"
MENU_MUSIC = "menu_music.mp3"
GAMEPLAY_MUSIC = "gameplay_music.mp3"

# --- UI Elements ---
UI_ROUND_RECT_RADIUS = 8
UI_BUTTON_HEIGHT = 30
UI_PADDING = 10 # General padding
UI_ELEMENT_PADDING = 8 # Padding between smaller elements within a group
UI_SECTION_PADDING = 15 # Padding between larger UI sections

UI_FONT_SIZE_XLARGE = 60
UI_FONT_SIZE_LARGE = 48
UI_FONT_SIZE_NORMAL = 28
UI_FONT_SIZE_SMALL = 24
UI_FONT_SIZE_XSMALL = 20

# Slider specific
UI_SLIDER_TRACK_HEIGHT = 8
UI_SLIDER_KNOB_RADIUS = 10
DMG_SLIDER_TRACK_COLOR = DMG_UI_BORDER
DMG_SLIDER_KNOB_COLOR = DMG_PRIMARY_GREEN
DMG_SLIDER_KNOB_OUTLINE = DMG_LIGHT_TEXT

# --- Reporting ---
REPORT_FILENAME = "maze_run_reports.txt"