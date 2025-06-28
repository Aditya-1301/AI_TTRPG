import curses
import subprocess
import sys
import os
from typing import Optional

class GameLauncher:
    """Handles launching the actual game session"""
    
    def __init__(self, session_uuid: str):
        self.session_uuid = session_uuid
    
    def launch_game(self) -> bool:
        """Launch the game with the specified session"""
        try:
            # End curses mode temporarily
            curses.endwin()
            
            # Get the path to the game script
            game_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'game', 'game.py')
            
            # Launch the game with the session UUID
            print(f"\nLaunching game session: {self.session_uuid}")
            print("=" * 50)
            
            # Create a subprocess to run the game
            env = os.environ.copy()
            env['TTRPG_SESSION_UUID'] = self.session_uuid
            
            # Run the game script
            result = subprocess.run([
                sys.executable, game_script
            ], env=env, cwd=os.path.dirname(game_script))
            
            print("\n" + "=" * 50)
            print("Game session ended. Press Enter to return to session manager...")
            input()
            
            # Reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error launching game: {e}")
            print("Press Enter to continue...")
            input()
            return False
    
    @staticmethod
    def launch_new_game() -> Optional[str]:
        """Launch a new game session and return the session UUID"""
        try:
            # End curses mode temporarily
            curses.endwin()
            
            # Get the path to the game script
            game_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'game', 'game.py')
            
            print("\nStarting new game session...")
            print("=" * 50)
            
            # Run the game script for a new session
            result = subprocess.run([
                sys.executable, game_script, '--new'
            ], cwd=os.path.dirname(game_script), capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract session UUID from output (this would need to be implemented in game.py)
                # For now, we'll return a placeholder
                session_uuid = "new-session-uuid"
                print(f"New session created: {session_uuid}")
            else:
                print("Failed to create new session")
                session_uuid = None
            
            print("\n" + "=" * 50)
            print("Press Enter to return to session manager...")
            input()
            
            # Reinitialize curses
            stdscr = curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.curs_set(0)
            
            return session_uuid
            
        except Exception as e:
            print(f"Error creating new game: {e}")
            print("Press Enter to continue...")
            input()
            return None

def integrate_with_existing_game():
    """
    Integration points with the existing game.py:
    
    1. Modify game.py to accept command line arguments:
       - --session-uuid <uuid>: Resume specific session
       - --new: Create new session
    
    2. Add environment variable support:
       - TTRPG_SESSION_UUID: Session to resume
    
    3. Return session UUID when creating new sessions
    
    Example modifications for game.py:
    
    ```python
    import argparse
    
    def parse_arguments():
        parser = argparse.ArgumentParser(description='TTRPG Game')
        parser.add_argument('--session-uuid', help='Resume specific session')
        parser.add_argument('--new', action='store_true', help='Create new session')
        return parser.parse_args()
    
    def main():
        args = parse_arguments()
        
        # Check for environment variable
        session_uuid = os.getenv('TTRPG_SESSION_UUID') or args.session_uuid
        
        if args.new or not session_uuid:
            # Create new session logic
            session_id, session_uuid = create_new_session()
            print(f"SESSION_UUID:{session_uuid}")  # For capture by launcher
        else:
            # Resume existing session
            session_id, session_uuid, conversation_history = load_session(session_uuid)
        
        # Continue with existing game logic...
    ```
    """
    pass