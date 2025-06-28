import curses
import textwrap
from datetime import datetime
from typing import List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

# Import from existing game logic
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.game import supabase, logger

class ViewState(Enum):
    SESSIONS_LIST = "sessions_list"
    SESSION_DETAIL = "session_detail"
    EDIT_PROMPT = "edit_prompt"
    EDIT_RULES = "edit_rules"

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
        self.system_prompt = ""
        self.rules_config = ""
        self.edit_buffer = ""
        self.cursor_pos = 0
        self.edit_scroll = 0
        
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
        """Load sessions from database"""
        try:
            # Get sessions with message counts and last messages
            sessions_response = supabase.table('sessions').select('*').order('created_at', desc=True).execute()
            
            self.sessions = []
            for session in sessions_response.data:
                # Get message count and last message for each session
                messages_response = supabase.table('messages').select('content, created_at').eq('session_id', session['id']).order('created_at', desc=True).limit(1).execute()
                
                last_message = ""
                if messages_response.data:
                    last_message = messages_response.data[0]['content'][:50] + "..." if len(messages_response.data[0]['content']) > 50 else messages_response.data[0]['content']
                
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
                
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            self.sessions = []
    
    def draw_header(self):
        """Draw the main header"""
        height, width = self.stdscr.getmaxyx()
        
        # Clear header area
        self.stdscr.addstr(0, 0, " " * width, curses.color_pair(1))
        
        # Title
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
        end_y = height - 3
        self.max_display_items = end_y - start_y
        
        # Clear content area
        for y in range(start_y, end_y):
            self.stdscr.addstr(y, 0, " " * width)
        
        if not self.sessions:
            no_sessions_msg = "No sessions found. Create a new session to get started."
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
            y_pos = start_y + i
            
            # Determine colors and attributes
            is_selected = session_index == self.selected_index
            color_pair = curses.color_pair(6) if is_selected else curses.color_pair(3)
            
            # Status indicator
            status = "●" if session.is_active else "○"
            status_color = curses.color_pair(2) if session.is_active else curses.color_pair(3)
            
            if is_selected:
                self.stdscr.addstr(y_pos, 0, " " * width, color_pair)
            
            # Draw session info
            self.stdscr.addstr(y_pos, 2, status, status_color | curses.A_BOLD)
            
            # Campaign title (use UUID as title for now)
            campaign_title = f"Campaign {session.session_uuid[:8]}"
            self.stdscr.addstr(y_pos, 4, campaign_title, color_pair | curses.A_BOLD)
            
            # System and date info
            system_info = f"System: D&D 5e"
            date_str = session.created_at[:10] if session.created_at else "Unknown"
            last_played = f"Last played: {date_str}"
            
            if y_pos + 1 < end_y:
                self.stdscr.addstr(y_pos + 1, 6, system_info, color_pair)
                date_x = width - len(last_played) - 4
                if date_x > len(system_info) + 10:
                    self.stdscr.addstr(y_pos + 1, date_x, last_played, color_pair)
            
            # Preview text
            if session.last_message and y_pos + 2 < end_y:
                preview = f'"{session.last_message}"'
                if len(preview) > width - 8:
                    preview = preview[:width - 11] + "..."
                self.stdscr.addstr(y_pos + 2, 6, preview, color_pair)
            
            # Add spacing between sessions
            if i < self.max_display_items - 1 and session_index < len(self.sessions) - 1:
                if y_pos + 3 < end_y:
                    self.stdscr.addstr(y_pos + 3, 0, " " * width)
    
    def draw_session_detail(self):
        """Draw the session detail view"""
        if not self.selected_session:
            return
            
        height, width = self.stdscr.getmaxyx()
        start_y = 3
        
        # Clear content area
        for y in range(start_y, height - 3):
            self.stdscr.addstr(y, 0, " " * width)
        
        # Campaign header
        campaign_title = f"Campaign {self.selected_session.session_uuid[:8]}"
        title_x = max(0, (width - len(campaign_title)) // 2)
        self.stdscr.addstr(start_y, title_x, campaign_title, curses.color_pair(1) | curses.A_BOLD)
        
        # System and date info
        system_info = "System: D&D 5e"
        date_str = self.selected_session.created_at[:10] if self.selected_session.created_at else "Unknown"
        last_played = f"Last played: {date_str}"
        
        info_line = f"{system_info} | {last_played}"
        info_x = max(0, (width - len(info_line)) // 2)
        self.stdscr.addstr(start_y + 1, info_x, info_line, curses.color_pair(3))
        
        # Configuration sections
        current_y = start_y + 3
        
        # System Prompt section
        self.stdscr.addstr(current_y, 2, "System Prompt Configuration:", curses.color_pair(1) | curses.A_BOLD)
        current_y += 1
        
        # System prompt box
        prompt_height = 8
        for i in range(prompt_height):
            if current_y + i < height - 3:
                self.stdscr.addstr(current_y + i, 4, "│" + " " * (width - 8) + "│", curses.color_pair(7))
        
        # Add some sample text
        sample_prompt = "You are an advanced AI Game Master for an immersive D&D campaign..."
        wrapped_prompt = textwrap.wrap(sample_prompt, width - 10)
        for i, line in enumerate(wrapped_prompt[:prompt_height-2]):
            if current_y + i + 1 < height - 3:
                self.stdscr.addstr(current_y + i + 1, 6, line, curses.color_pair(3))
        
        current_y += prompt_height + 1
        
        # Rules Configuration section
        if current_y < height - 8:
            self.stdscr.addstr(current_y, 2, "Game Rules Configuration:", curses.color_pair(1) | curses.A_BOLD)
            current_y += 1
            
            # Rules box
            rules_height = 6
            for i in range(rules_height):
                if current_y + i < height - 3:
                    self.stdscr.addstr(current_y + i, 4, "│" + " " * (width - 8) + "│", curses.color_pair(7))
            
            # Add sample rules
            sample_rules = "Combat: Turn-based initiative system\nMagic: Standard D&D 5e spellcasting\nSkill Checks: D20 + modifier vs DC"
            rules_lines = sample_rules.split('\n')
            for i, line in enumerate(rules_lines[:rules_height-2]):
                if current_y + i + 1 < height - 3:
                    self.stdscr.addstr(current_y + i + 1, 6, line, curses.color_pair(3))
    
    def draw_footer(self):
        """Draw the footer with navigation help"""
        height, width = self.stdscr.getmaxyx()
        footer_y = height - 2
        
        # Clear footer
        self.stdscr.addstr(footer_y, 0, " " * width, curses.color_pair(1))
        self.stdscr.addstr(footer_y + 1, 0, " " * width, curses.color_pair(1))
        
        if self.current_view == ViewState.SESSIONS_LIST:
            help_text = "↑↓: Navigate | Enter: Select | N: New Session | D: Delete | Q: Quit"
            if self.sessions:
                page_info = f"Page {self.scroll_offset // self.max_display_items + 1} of {(len(self.sessions) - 1) // self.max_display_items + 1}"
                page_x = width - len(page_info) - 2
                self.stdscr.addstr(footer_y + 1, page_x, page_info, curses.color_pair(3))
        elif self.current_view == ViewState.SESSION_DETAIL:
            help_text = "Tab: Switch fields | Enter: Start Game | Esc: Back | Ctrl+S: Save"
        else:
            help_text = "Esc: Back | Ctrl+S: Save"
        
        self.stdscr.addstr(footer_y, 2, help_text, curses.color_pair(3))
    
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
    
    def handle_session_detail_input(self, key):
        """Handle input in session detail view"""
        if key == 27:  # Escape
            self.current_view = ViewState.SESSIONS_LIST
        elif key == ord('\n') or key == curses.KEY_ENTER:
            self.start_game_session()
        elif key == 19:  # Ctrl+S
            self.save_session_config()
    
    def create_new_session(self):
        """Create a new session"""
        try:
            response = supabase.table('sessions').insert({}).execute()
            if response.data:
                self.load_sessions()  # Refresh the list
                # Select the new session (it will be at the top due to ordering)
                self.selected_index = 0
        except Exception as e:
            logger.error(f"Error creating new session: {e}")
    
    def delete_selected_session(self):
        """Delete the selected session"""
        if not self.sessions or self.selected_index >= len(self.sessions):
            return
            
        try:
            session = self.sessions[self.selected_index]
            supabase.table('sessions').delete().eq('session_uuid', session.session_uuid).execute()
            self.load_sessions()  # Refresh the list
            
            # Adjust selected index if necessary
            if self.selected_index >= len(self.sessions) and self.sessions:
                self.selected_index = len(self.sessions) - 1
            elif not self.sessions:
                self.selected_index = 0
                
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
    
    def start_game_session(self):
        """Start the selected game session"""
        if self.selected_session:
            # This would integrate with your existing game.py main() function
            # For now, we'll just show a message
            curses.endwin()
            print(f"Starting game session: {self.selected_session.session_uuid}")
            print("This would launch the game with the selected session...")
            print("Press Enter to return to session manager...")
            input()
            curses.doupdate()
    
    def save_session_config(self):
        """Save session configuration"""
        # This would save the system prompt and rules configuration
        # Implementation depends on how you want to store this data
        pass
    
    def run(self):
        """Main UI loop"""
        self.stdscr.clear()
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)
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