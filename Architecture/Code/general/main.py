# main.py - Main entry point for the music application with Learn/Create selection

import pygame
import sys
from learn import main as learn_main
from music_creation import MusicCreator

# Constants
WIDTH, HEIGHT = 1600, 900

def initialize_pygame():
    """Initialize pygame and return the screen and fonts"""
    pygame.init()
    pygame.font.init()  # Explicitly initialize the font module
    
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Music Application")
    
    # Initialize fonts
    title_font = pygame.font.Font(None, 64)
    button_font = pygame.font.Font(None, 48)
    instruction_font = pygame.font.Font(None, 28)
    
    return screen, title_font, button_font, instruction_font

# Colors
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (50, 50, 50)
BUTTON_HOVER_COLOR = (70, 70, 70)
BUTTON_SELECTED_COLOR = (0, 100, 200)

# Fonts will be initialized in the main function

def draw_button(surface, text, position, size, color, text_color, font, selected=False):
    """Draw a button with text on the given surface"""
    # Draw button background
    rect = pygame.Rect(position, size)
    pygame.draw.rect(surface, color, rect, border_radius=10)
    
    # Draw border (thicker if selected)
    border_width = 4 if selected else 2
    border_color = BUTTON_SELECTED_COLOR if selected else (200, 200, 200)
    pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=10)
    
    # Draw text
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=(position[0] + size[0]//2, position[1] + size[1]//2))
    surface.blit(text_surface, text_rect)
    
    return rect

def main():
    """Main function to run the menu and launch selected mode"""
    selected_button = 0  # 0 for Learn, 1 for Create
    
    # Initialize pygame and get screen and fonts
    screen, title_font, button_font, instruction_font = initialize_pygame()
    
    # Main loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                # 'A' key to switch between buttons
                if event.key == pygame.K_a:
                    selected_button = 1 - selected_button  # Toggle between 0 and 1
                
                # Enter key to select
                elif event.key == pygame.K_RETURN:
                    if selected_button == 0:
                        # Launch Learn mode
                        pygame.quit()
                        learn_main()
                        # Re-initialize pygame when returning
                        screen, title_font, button_font, instruction_font = initialize_pygame()
                    else:
                        # Launch Create mode
                        pygame.quit()
                        creator = MusicCreator()
                        creator.run()
                        # Re-initialize pygame when returning
                        screen, title_font, button_font, instruction_font = initialize_pygame()
                        
                # Escape to quit
                elif event.key == pygame.K_ESCAPE:
                    running = False
        
        # Clear screen
        screen.fill(BACKGROUND_COLOR)
        
        # Draw title
        title_text = title_font.render("Music Application", True, TEXT_COLOR)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 100))
        
        # Draw buttons
        learn_button_rect = draw_button(
            screen, "Learn", 
            (WIDTH//4 - 100, HEIGHT//2 - 40), 
            (200, 80), 
            BUTTON_COLOR if selected_button != 0 else BUTTON_SELECTED_COLOR, 
            TEXT_COLOR,
            button_font,
            selected_button == 0
        )
        
        create_button_rect = draw_button(
            screen, "Create", 
            (WIDTH - WIDTH//4 - 100, HEIGHT//2 - 40), 
            (200, 80), 
            BUTTON_COLOR if selected_button != 1 else BUTTON_SELECTED_COLOR, 
            TEXT_COLOR,
            button_font,
            selected_button == 1
        )
        
        # Draw instructions
        instr1 = instruction_font.render("Press 'A' to switch between options", True, (200, 200, 200))
        instr2 = instruction_font.render("Press 'Enter' to select", True, (200, 200, 200))
        instr3 = instruction_font.render("Press 'Esc' to quit", True, (200, 200, 200))
        
        screen.blit(instr1, (WIDTH//2 - instr1.get_width()//2, HEIGHT - 120))
        screen.blit(instr2, (WIDTH//2 - instr2.get_width()//2, HEIGHT - 90))
        screen.blit(instr3, (WIDTH//2 - instr3.get_width()//2, HEIGHT - 60))
        
        # Update display
        pygame.display.flip()
        
        # Cap at 60 FPS
        pygame.time.Clock().tick(60)
    
    # Clean up
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
