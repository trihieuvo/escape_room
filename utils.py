import pygame
import os
import sys
from constants import FALLBACK_IMAGE_COLOR, IMAGE_FOLDER, SOUNDS_FOLDER, UI_ROUND_RECT_RADIUS

def load_scaled_image(filename, new_size):
    """Loads an image, scales it, and handles errors by returning a fallback surface."""
    try:
        image_path = os.path.join(IMAGE_FOLDER, filename)
        if not os.path.exists(image_path):
            if isinstance(new_size, int): new_size = (new_size, new_size)
            fallback_surface = pygame.Surface(new_size)
            fallback_surface.fill(FALLBACK_IMAGE_COLOR)
            if new_size[0] > 1 and new_size[1] > 1:
                 pygame.draw.line(fallback_surface, (0,0,0), (0,0), (new_size[0]-1, new_size[1]-1),1)
                 pygame.draw.line(fallback_surface, (0,0,0), (0,new_size[1]-1), (new_size[0]-1,0),1)
            return fallback_surface

        image = pygame.image.load(image_path)
        try:
            image = image.convert_alpha()
        except pygame.error: 
            image = image.convert()
            
        if isinstance(new_size, int):
            scale_to = (new_size, new_size)
        elif isinstance(new_size, tuple) and len(new_size) == 2:
            scale_to = new_size
        else: 
            scale_to = image.get_size()

        if image.get_size() != scale_to:
            image = pygame.transform.smoothscale(image, scale_to)
        return image

    except (pygame.error, Exception) as e: 
        print(f"ERROR loading/scaling image '{filename}': {e}", file=sys.stderr)
        if isinstance(new_size, int): new_size = (new_size, new_size)
        fallback_surface_size = new_size if isinstance(new_size, tuple) and len(new_size) == 2 else (20,20) 
        fallback_surface = pygame.Surface(fallback_surface_size)
        fallback_surface.fill(FALLBACK_IMAGE_COLOR)
        if fallback_surface_size[0] > 1 and fallback_surface_size[1] > 1:
             pygame.draw.line(fallback_surface, (0,0,0), (0,0), (fallback_surface_size[0]-1, fallback_surface_size[1]-1),1)
             pygame.draw.line(fallback_surface, (0,0,0), (0,fallback_surface_size[1]-1), (fallback_surface_size[0]-1,0),1)
        return fallback_surface

def load_sound(filename):
    """Loads a sound file and handles errors by returning None."""
    if not pygame.mixer.get_init(): 
        return None
    try:
        sound_path = os.path.join(SOUNDS_FOLDER, filename)
        if not os.path.exists(sound_path):
            print(f"Warning: Sound file not found: {sound_path}", file=sys.stderr)
            return None
        sound = pygame.mixer.Sound(sound_path)
        return sound
    except pygame.error as e:
        print(f"ERROR loading sound '{filename}': {e}", file=sys.stderr)
        return None

def draw_rounded_rect(surface, color, rect, radius, border_thickness=0, border_color=None, border_hover_color=None, is_hovered=False):
    """
    Draws a rectangle with rounded corners.
    Supports fill, border, and hover state for border.
    """
    final_border_color = border_color
    if is_hovered and border_hover_color:
        final_border_color = border_hover_color

    if border_thickness > 0 and final_border_color:
        # Draw outer border rect
        pygame.draw.rect(surface, final_border_color, rect, border_thickness, border_radius=radius)
        
        inner_rect_params = (rect.x + border_thickness, 
                             rect.y + border_thickness,
                             rect.width - 2 * border_thickness,
                             rect.height - 2 * border_thickness)
        if inner_rect_params[2] > 0 and inner_rect_params[3] > 0:
            inner_rect = pygame.Rect(*inner_rect_params)
            inner_radius = max(0, radius - border_thickness)
            pygame.draw.rect(surface, color, inner_rect, 0, border_radius=inner_radius)
        elif inner_rect_params[2] <= 0 or inner_rect_params[3] <= 0 :
             pygame.draw.rect(surface, color, rect, 0, border_radius=radius)


    else: 
        pygame.draw.rect(surface, color, rect, 0, border_radius=radius)

def draw_text(surface, text, font, color, center_pos, antialias=True, background_color=None, padding=0):
    """Draws text centered at a given position, optionally with a background."""
    text_surface = font.render(text, antialias, color)
    text_rect = text_surface.get_rect(center=center_pos)

    if background_color:
        bg_rect = text_rect.inflate(padding * 2, padding * 2)
        pygame.draw.rect(surface, background_color, bg_rect, border_radius=UI_ROUND_RECT_RADIUS // 2 if padding > 2 else 0)

    surface.blit(text_surface, text_rect)
    return text_rect