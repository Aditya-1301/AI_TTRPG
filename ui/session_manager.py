import curses
import textwrap
from datetime import datetime
from typing import List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import subprocess
import sys
import os

# Import from existing game logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import supabase, logger, create_new_session, load_session

class ViewState(Enum):
    SESSIONS_LIST = "sessions_list"
    SESSION_DETAIL = "session_detail"

@dataclass
class SessionData:
    id: int
    session_uuid: str
    created_at: str
    last_message: str = ""
    message_count: int = 0
    is_active: bool = False

class TTRPGSessionManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_view = ViewState.SESSIONS_LIST
        self.sessions: List[SessionData] = []
        self.selected_index = 0
        self.selected_session: Optional[SessionData] = None
        self.scroll_offset = 0
        self.max_display_items = 0
        self.status_message = ""
        self.status_type = "info"
        
        # Initialize colors
        self.init_colors()
        
        # Load initial data
        self.load_sessions()
        
    def init_colors(self):
        """Initialize color pairs for the UI"""
        curses.start_color()
        curses.use_default_colors()
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Headers
        curses.init_pair(2, curses.COLOR_GREEN, -1)   # Active/Success
        curses.init_pair(3, curses.COLOR_WHITE, -1)   # Normal text
        curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Highlights
        curses.init_pair(5, curses.COLOR_RED, -1)     # Errors
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE) # Input fields
        
    def load_sessions(self):
        """Load sessions from database using existing game.py functions"""
        try:
            # Get sessions with message counts and last messages
            sessions_response = supabase.table('sessions').select('*').order('created_at', desc=True).execute()
            
            self.sessions = []
            for session in sessions_response.data:
                # Get message count and last message for each session
                messages_response = supabase.table('messages').select('content, created_at, role').eq('session_id', session['id']).order('created_at', desc=True).limit(1).execute()
                
                last_message = ""
                if messages_response.data:
                    msg = messages_response.data[0]
                    # Show GM messages preferentially, or user messages if no GM messages
                    if msg['role'] == 'model':
                        last_message = f"GM: {msg['content'][:47]}..." if len(msg['content']) > 47 else f"GM: {msg['content']}"
                    else:
                        last_message = f"Player: {msg['content'][:44]}..." if len(msg['content']) > 44 else f"Player: {msg['content']}"
                
                count_response = supabase.table('messages').select('id', count='exact').eq('session_id', session['id']).execute()
                message_count = count_response.count or 0
                
                session_data = SessionData(
                    id=session['id'],
                    session_uuid=session['session_uuid'],
                    created_at=session['created_at'],
                    last_message=last_message,
                    message_count=message_count,
                    is_active=message_count > 0
                )
                self.sessions.append(session_data)
                
            self.set_status(f"Loaded {len(self.sessions)} sessions", "success")
                
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            self.sessions = []
            self.set_status(f"Error loading sessions: {str(e)}", "error")
    
    def set_status(self, message: str, message_type: str = "info"):
        """Set status message"""
        self.status_message = message
        self.status_type = message_type
    
    def draw_header(self):
        """Draw the main header"""
        height, width = self.stdscr.getmaxyx()
        
        # Clear header area
        self.stdscr.addstr(0, 0, " " * width, curses.color_pair(1))
        
        # Title
        title = "🎲 TTRPG Sessions Manager"
        title_x = max(0, (width - len(title)) // 2)
        try:
            self.stdscr.addstr(0, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            # Fallback without emoji if terminal doesn't support it
            title = "TTRPG Sessions Manager"
            title_x = max(0, (width - len(title)) // 2)
            self.stdscr.addstr(0, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Session count and date
        session_count = f"Sessions: {len(self.sessions)}"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Left side - session count
        self.stdscr.addstr(1, 2, session_count, curses.color_pair(3))
        
        # Right side - current time
        time_x = max(0, width - len(current_time) - 2)
        self.stdscr.addstr(1, time_x, current_time, curses.color_pair(3))
        
        # Separator line
        self.stdscr.addstr(2, 0, "─" * width, curses.color_pair(1))
    
    def draw_sessions_list(self):
        """Draw the sessions list view"""
        height, width = self.stdscr.getmaxyx()
        
        # Calculate display area
        start_y = 3
        end_y = height - 4  # Leave space for status and footer
        self.max_display_items = (end_y - start_y) // 4  # Each session takes ~4 lines
        
        # Clear content area
        for y in range(start_y, end_y):
            try:
                self.stdscr.addstr(y, 0, " " * width)
            except curses.error:
                pass
        
        if not self.sessions:
            no_sessions_msg = "No sessions found. Press 'N' to create a new session."
            msg_x = max(0, (width - len(no_sessions_msg)) // 2)
            self.stdscr.addstr(start_y + 2, msg_x, no_sessions_msg, curses.color_pair(4))
            return
        
        # Adjust scroll offset
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_display_items:
            self.scroll_offset = self.selected_index - self.max_display_items + 1
        
        # Draw sessions
        for i in range(self.max_display_items):
            session_index = i + self.scroll_offset
            if session_index >= len(self.sessions):
                break
                
            session = self.sessions[session_index]
            y_pos = start_y + (i * 4)
            
            if y_pos + 3 >= end_y:
                break
            
            # Determine colors and attributes
            is_selected = session_index == self.selected_index
            color_pair = curses.color_pair(6) if is_selected else curses.color_pair(3)
            
            # Status indicator
            status = "●" if session.is_active else "○"
            status_color = curses.color_pair(2) if session.is_active else curses.color_pair(3)
            
            if is_selected:
                # Highlight entire session block
                for line_offset in range(4):
                    if y_pos + line_offset < end_y:
                        try:
                            self.stdscr.addstr(y_pos + line_offset, 0, " " * width, color_pair)
                        except curses.error:
                            pass
            
            # Draw session info
            try:
                self.stdscr.addstr(y_pos, 2, status, status_color | curses.A_BOLD)
                
                # Campaign title (use UUID as title for now)
                campaign_title = f"Campaign {session.session_uuid[:8]}"
                self.stdscr.addstr(y_pos, 4, campaign_title, color_pair | curses.A_BOLD)
                
                # Message count
                msg_count = f"({session.message_count} messages)"
                count_x = min(width - len(msg_count) - 2, 4 + len(campaign_title) + 2)
                self.stdscr.addstr(y_pos, count_x, msg_count, color_pair)
                
                # System and date info
                system_info = "System: Gemini AI GM"
                date_str = session.created_at[:10] if session.created_at else "Unknown"
                last_played = f"Created: {date_str}"
                
                self.stdscr.addstr(y_pos + 1, 6, system_info, color_pair)
                date_x = width - len(last_played) - 4
                if date_x > len(system_info) + 10:
                    self.stdscr.addstr(y_pos + 1, date_x, last_played, color_pair)
                
                # Preview text
                if session.last_message:
                    preview = f'"{session.last_message}"'
                    if len(preview) > width - 8:
                        preview = preview[:width - 11] + "..."
                    self.stdscr.addstr(y_pos + 2, 6, preview, color_pair)
                else:
                    self.stdscr.addstr(y_pos + 2, 6, '"No messages yet"', color_pair)
                    
            except curses.error:
                pass
    
    def draw_session_detail(self):
        """Draw the session detail view"""
        if not self.selected_session:
            return
            
        height, width = self.stdscr.getmaxyx()
        start_y = 3
        
        # Clear content area
        for y in range(start_y, height - 4):
            try:
                self.stdscr.addstr(y, 0, " " * width)
            except curses.error:
                pass
        
        # Campaign header
        campaign_title = f"Campaign {self.selected_session.session_uuid[:8]}"
        title_x = max(0, (width - len(campaign_title)) // 2)
        try:
            self.stdscr.addstr(start_y, title_x, campaign_title, curses.color_pair(1) | curses.A_BOLD)
            
            # System and date info
            system_info = "System: Gemini AI GM"
            date_str = self.selected_session.created_at[:10] if self.selected_session.created_at else "Unknown"
            last_played = f"Created: {date_str} | Messages: {self.selected_session.message_count}"
            
            info_x = max(0, (width - len(last_played)) // 2)
            self.stdscr.addstr(start_y + 1, info_x, last_played, curses.color_pair(3))
            
            # Session UUID
            uuid_info = f"UUID: {self.selected_session.session_uuid}"
            uuid_x = max(0, (width - len(uuid_info)) // 2)
            self.stdscr.addstr(start_y + 2, uuid_x, uuid_info, curses.color_pair(4))
            
            # Action buttons
            current_y = start_y + 5
            
            # Start/Resume Game button
            if self.selected_session.is_active:
                button_text = "[ Resume Game Session ]"
                action_text = "Resume this campaign where you left off"
            else:
                button_text = "[ Start New Game Session ]"
                action_text = "Begin a new adventure in this campaign"
            
            button_x = max(0, (width - len(button_text)) // 2)
            self.stdscr.addstr(current_y, button_x, button_text, curses.color_pair(2) | curses.A_BOLD)
            
            action_x = max(0, (width - len(action_text)) // 2)
            self.stdscr.addstr(current_y + 1, action_x, action_text, curses.color_pair(3))
            
            # Session info
            current_y += 4
            self.stdscr.addstr(current_y, 2, "Session Information:", curses.color_pair(1) | curses.A_BOLD)
            current_y += 1
            
            info_lines = [
                f"• Session ID: {self.selected_session.id}",
                f"• UUID: {self.selected_session.session_uuid}",
                f"• Created: {self.selected_session.created_at}",
                f"• Message Count: {self.selected_session.message_count}",
                f"• Status: {'Active' if self.selected_session.is_active else 'Inactive'}"
            ]
            
            for line in info_lines:
                if current_y < height - 6:
                    self.stdscr.addstr(current_y, 4, line, curses.color_pair(3))
                    current_y += 1
                    
        except curses.error:
            pass
    
    def draw_status_bar(self):
        """Draw status bar"""
        height, width = self.stdscr.getmaxyx()
        status_y = height - 3
        
        # Clear status line
        try:
            self.stdscr.addstr(status_y, 0, " " * width)
            
            if self.status_message:
                # Choose color based on message type
                if self.status_type == "error":
                    color_pair = curses.color_pair(5)  # Red
                elif self.status_type == "success":
                    color_pair = curses.color_pair(2)  # Green
                elif self.status_type == "warning":
                    color_pair = curses.color_pair(4)  # Yellow
                else:
                    color_pair = curses.color_pair(3)  # Normal
                
                # Truncate message if too long
                display_message = self.status_message
                if len(display_message) > width - 4:
                    display_message = display_message[:width - 7] + "..."
                
                self.stdscr.addstr(status_y, 2, display_message, color_pair)
        except curses.error:
            pass
    
    def draw_footer(self):
        """Draw the footer with navigation help"""
        height, width = self.stdscr.getmaxyx()
        footer_y = height - 2
        
        # Clear footer
        try:
            self.stdscr.addstr(footer_y, 0, " " * width, curses.color_pair(1))
            self.stdscr.addstr(footer_y + 1, 0, " " * width, curses.color_pair(1))
            
            if self.current_view == ViewState.SESSIONS_LIST:
                help_text = "↑↓: Navigate | Enter: Select | N: New Session | D: Delete | R: Refresh | Q: Quit"
                if self.sessions:
                    total_pages = (len(self.sessions) - 1) // self.max_display_items + 1 if self.max_display_items > 0 else 1
                    current_page = self.scroll_offset // self.max_display_items + 1 if self.max_display_items > 0 else 1
                    page_info = f"Page {current_page} of {total_pages}"
                    page_x = width - len(page_info) - 2
                    self.stdscr.addstr(footer_y + 1, page_x, page_info, curses.color_pair(3))
            elif self.current_view == ViewState.SESSION_DETAIL:
                help_text = "Enter: Start/Resume Game | D: Delete Session | Esc: Back | Q: Quit"
            
            self.stdscr.addstr(footer_y, 2, help_text, curses.color_pair(3))
        except curses.error:
            pass
    
    def handle_sessions_list_input(self, key):
        """Handle input in sessions list view"""
        if key == curses.KEY_UP and self.selected_index > 0:
            self.selected_index -= 1
        elif key == curses.KEY_DOWN and self.selected_index < len(self.sessions) - 1:
            self.selected_index += 1
        elif key == ord('\n') or key == curses.KEY_ENTER:
            if self.sessions and self.selected_index < len(self.sessions):
                self.selected_session = self.sessions[self.selected_index]
                self.current_view = ViewState.SESSION_DETAIL
        elif key == ord('n') or key == ord('N'):
            self.create_new_session()
        elif key == ord('d') or key == ord('D'):
            self.delete_selected_session()
        elif key == ord('r') or key == ord('R'):
            self.load_sessions()  # Refresh
            self.set_status("Sessions refreshed", "success")
    
    def handle_session_detail_input(self, key):
        """Handle input in session detail view"""
        if key == 27:  # Escape
            self.current_view = ViewState.SESSIONS_LIST
        elif key == ord('\n') or key == curses.KEY_ENTER:
            self.start_game_session()
        elif key == ord('d') or key == ord('D'):
            self.delete_current_session()
    
    def create_new_session(self):
        """Create a new session using existing game.py function"""
        try:
            self.set_status("Creating new session...", "info")
            session_id, session_uuid = create_new_session()
            if session_id and session_uuid:
                self.load_sessions()  # Refresh the list
                # Select the new session (it will be at the top due to ordering)
                self.selected_index = 0
                self.set_status(f"New session created: {session_uuid[:8]}", "success")
            else:
                self.set_status("Failed to create new session", "error")
        except Exception as e:
            logger.error(f"Error creating new session: {e}")
            self.set_status(f"Error creating session: {str(e)}", "error")
    
    def delete_selected_session(self):
        """Delete the selected session"""
        if not self.sessions or self.selected_index >= len(self.sessions):
            return
            
        try:
            session = self.sessions[self.selected_index]
            # Simple confirmation - in a real implementation you might want a proper dialog
            self.set_status(f"Press 'Y' to confirm deletion of session {session.session_uuid[:8]}", "warning")
            self.stdscr.refresh()
            
            # Wait for confirmation
            confirm_key = self.stdscr.getch()
            if confirm_key == ord('y') or confirm_key == ord('Y'):
                supabase.table('sessions').delete().eq('session_uuid', session.session_uuid).execute()
                self.load_sessions()  # Refresh the list
                
                # Adjust selected index if necessary
                if self.selected_index >= len(self.sessions) and self.sessions:
                    self.selected_index = len(self.sessions) - 1
                elif not self.sessions:
                    self.selected_index = 0
                
                self.set_status(f"Session {session.session_uuid[:8]} deleted", "success")
            else:
                self.set_status("Deletion cancelled", "info")
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            self.set_status(f"Error deleting session: {str(e)}", "error")
    
    def delete_current_session(self):
        """Delete the currently viewed session"""
        if not self.selected_session:
            return
            
        try:
            # Simple confirmation
            self.set_status(f"Press 'Y' to confirm deletion of session {self.selected_session.session_uuid[:8]}", "warning")
            self.stdscr.refresh()
            
            # Wait for confirmation
            confirm_key = self.stdscr.getch()
            if confirm_key == ord('y') or confirm_key == ord('Y'):
                supabase.table('sessions').delete().eq('session_uuid', self.selected_session.session_uuid).execute()
                self.current_view = ViewState.SESSIONS_LIST
                self.load_sessions()  # Refresh the list
                
                # Adjust selected index if necessary
                if self.selected_index >= len(self.sessions) and self.sessions:
                    self.selected_index = len(self.sessions) - 1
                elif not self.sessions:
                    self.selected_index = 0
                
                self.set_status(f"Session {self.selected_session.session_uuid[:8]} deleted", "success")
                self.selected_session = None
            else:
                self.set_status("Deletion cancelled", "info")
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            self.set_status(f"Error deleting session: {str(e)}", "error")
    
    def start_game_session(self):
        """Start the selected game session using existing game.py"""
        if not self.selected_session:
            return
            
        try:
            # End curses mode temporarily
            curses.endwin()
            
            # Get the path to the game script
            game_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'game', 'game.py')
            
            print(f"\nLaunching game session: {self.selected_session.session_uuid}")
            print("=" * 60)
            
            # Set environment variable for the session UUID
            env = os.environ.copy()
            env['TTRPG_RESUME_SESSION'] = self.selected_session.session_uuid
            
            # Run the game script
            result = subprocess.run([
                sys.executable, game_script
            ], env=env, cwd=os.path.dirname(game_script))
            
            print("\n" + "=" * 60)
            print("Game session ended. Press Enter to return to session manager...")
            input()
            
            # Reinitialize curses
            self.stdscr = curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)
            curses.curs_set(0)
            self.init_colors()
            
            # Refresh sessions in case anything changed
            self.load_sessions()
            self.set_status("Returned from game session", "success")
            
        except Exception as e:
            logger.error(f"Error launching game: {e}")
            self.set_status(f"Error launching game: {str(e)}", "error")
            
            # Make sure curses is reinitialized even if there's an error
            try:
                self.stdscr = curses.initscr()
                curses.start_color()
                curses.use_default_colors()
                curses.noecho()
                curses.cbreak()
                self.stdscr.keypad(True)
                curses.curs_set(0)
                self.init_colors()
            except:
                pass
    
    def run(self):
        """Main UI loop"""
        self.stdscr.clear()
        self.stdscr.nodelay(False)  # Block on input
        self.stdscr.timeout(-1)     # Wait indefinitely for input
        curses.curs_set(0)  # Hide cursor
        
        while True:
            try:
                # Clear screen
                self.stdscr.clear()
                
                # Draw UI components
                self.draw_header()
                
                if self.current_view == ViewState.SESSIONS_LIST:
                    self.draw_sessions_list()
                elif self.current_view == ViewState.SESSION_DETAIL:
                    self.draw_session_detail()
                
                self.draw_status_bar()
                self.draw_footer()
                
                # Refresh screen
                self.stdscr.refresh()
                
                # Handle input
                key = self.stdscr.getch()
                
                if key == ord('q') or key == ord('Q'):
                    if self.current_view == ViewState.SESSIONS_LIST:
                        break
                    else:
                        self.current_view = ViewState.SESSIONS_LIST
                elif self.current_view == ViewState.SESSIONS_LIST:
                    self.handle_sessions_list_input(key)
                elif self.current_view == ViewState.SESSION_DETAIL:
                    self.handle_session_detail_input(key)
                    
            except KeyboardInterrupt:
                break
            except curses.error:
                # Handle terminal resize or other curses errors
                pass

def main():
    """Main entry point"""
    try:
        curses.wrapper(lambda stdscr: TTRPGSessionManager(stdscr).run())
    except Exception as e:
        logger.error(f"UI Error: {e}")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()