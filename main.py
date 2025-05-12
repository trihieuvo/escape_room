import pygame
import sys
from game import Game 

if __name__ == '__main__':
    maze_game = Game()
    try:
        maze_game.run()
    except Exception as e:
        print(f"\nAn error occurred during game execution: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() 
        if pygame.get_init(): 
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.quit()
        sys.exit(1)