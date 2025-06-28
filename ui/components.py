import curses
import textwrap
from typing import List, Tuple, Optional

class TextBox:
    """A multi-line text input component"""
    
    def __init__(self, x: int, y: int, width: int, height: int, initial_text: str = ""):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.lines = initial_text.split('\n') if initial_text else ['']
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
        self.is_focused = False
        
    def draw(self, stdscr, color_pair: int):
        """Draw the text box"""
        # Draw border
        for i in range(self.height):
            line = " " * (self.width - 2)
            if i == 0:
                line = "┌" + "─" * (self.width - 2) + "┐"
            elif i == self.height - 1:
                line = "└" + "─" * (self.width - 2) + "┘"
            else:
                line = "│" + " " * (self.width - 2) + "│"
            
            try:
                stdscr.addstr(self.y + i, self.x, line, color_pair)
            except curses.error:
                pass
        
        # Draw content
        visible_lines = self.height - 2
        start_line = self.scroll_offset
        end_line = min(start_line + visible_lines, len(self.lines))
        
        for i in range(visible_lines):
            line_idx = start_line + i
            content_y = self.y + 1 + i
            content_x = self.x + 1
            
            if line_idx < len(self.lines):
                line_text = self.lines[line_idx]
                # Truncate line if too long
                if len(line_text) > self.width - 2:
                    line_text = line_text[:self.width - 5] + "..."
                
                try:
                    stdscr.addstr(content_y, content_x, line_text, color_pair)
                except curses.error:
                    pass
        
        # Draw cursor if focused
        if self.is_focused:
            cursor_y = self.y + 1 + (self.cursor_line - self.scroll_offset)
            cursor_x = self.x + 1 + min(self.cursor_col, self.width - 3)
            
            if (0 <= self.cursor_line - self.scroll_offset < visible_lines and 
                0 <= cursor_x - self.x - 1 < self.width - 2):
                try:
                    stdscr.addstr(cursor_y, cursor_x, " ", color_pair | curses.A_REVERSE)
                except curses.error:
                    pass
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input. Returns True if input was handled."""
        if not self.is_focused:
            return False
        
        if key == curses.KEY_UP:
            if self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
                self._adjust_scroll()
        elif key == curses.KEY_DOWN:
            if self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
                self._adjust_scroll()
        elif key == curses.KEY_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = len(self.lines[self.cursor_line])
                self._adjust_scroll()
        elif key == curses.KEY_RIGHT:
            if self.cursor_col < len(self.lines[self.cursor_line]):
                self.cursor_col += 1
            elif self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = 0
                self._adjust_scroll()
        elif key == curses.KEY_HOME:
            self.cursor_col = 0
        elif key == curses.KEY_END:
            self.cursor_col = len(self.lines[self.cursor_line])
        elif key == ord('\n') or key == curses.KEY_ENTER:
            # Insert new line
            current_line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = current_line[:self.cursor_col]
            self.lines.insert(self.cursor_line + 1, current_line[self.cursor_col:])
            self.cursor_line += 1
            self.cursor_col = 0
            self._adjust_scroll()
        elif key == curses.KEY_BACKSPACE or key == 127:
            if self.cursor_col > 0:
                line = self.lines[self.cursor_line]
                self.lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                # Join with previous line
                prev_line = self.lines[self.cursor_line - 1]
                current_line = self.lines[self.cursor_line]
                self.lines[self.cursor_line - 1] = prev_line + current_line
                del self.lines[self.cursor_line]
                self.cursor_line -= 1
                self.cursor_col = len(prev_line)
                self._adjust_scroll()
        elif key == curses.KEY_DC:  # Delete key
            if self.cursor_col < len(self.lines[self.cursor_line]):
                line = self.lines[self.cursor_line]
                self.lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col+1:]
            elif self.cursor_line < len(self.lines) - 1:
                # Join with next line
                current_line = self.lines[self.cursor_line]
                next_line = self.lines[self.cursor_line + 1]
                self.lines[self.cursor_line] = current_line + next_line
                del self.lines[self.cursor_line + 1]
        elif 32 <= key <= 126:  # Printable characters
            char = chr(key)
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col] + char + line[self.cursor_col:]
            self.cursor_col += 1
        else:
            return False
        
        return True
    
    def _adjust_scroll(self):
        """Adjust scroll offset to keep cursor visible"""
        visible_lines = self.height - 2
        
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.cursor_line - visible_lines + 1
    
    def get_text(self) -> str:
        """Get the current text content"""
        return '\n'.join(self.lines)
    
    def set_text(self, text: str):
        """Set the text content"""
        self.lines = text.split('\n') if text else ['']
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
    
    def focus(self):
        """Give focus to this text box"""
        self.is_focused = True
    
    def unfocus(self):
        """Remove focus from this text box"""
        self.is_focused = False

class Button:
    """A clickable button component"""
    
    def __init__(self, x: int, y: int, text: str, width: int = None):
        self.x = x
        self.y = y
        self.text = text
        self.width = width or len(text) + 4
        self.is_focused = False
        self.is_pressed = False
    
    def draw(self, stdscr, color_pair: int):
        """Draw the button"""
        # Button appearance
        if self.is_pressed:
            button_text = f"[{self.text.center(self.width - 2)}]"
            attr = color_pair | curses.A_REVERSE
        elif self.is_focused:
            button_text = f"[{self.text.center(self.width - 2)}]"
            attr = color_pair | curses.A_BOLD
        else:
            button_text = f" {self.text.center(self.width - 2)} "
            attr = color_pair
        
        try:
            stdscr.addstr(self.y, self.x, button_text, attr)
        except curses.error:
            pass
    
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input. Returns True if button was activated."""
        if not self.is_focused:
            return False
        
        if key == ord(' ') or key == ord('\n') or key == curses.KEY_ENTER:
            self.is_pressed = True
            return True
        
        return False
    
    def focus(self):
        """Give focus to this button"""
        self.is_focused = True
    
    def unfocus(self):
        """Remove focus from this button"""
        self.is_focused = False
        self.is_pressed = False

class StatusBar:
    """A status bar component for showing messages"""
    
    def __init__(self, x: int, y: int, width: int):
        self.x = x
        self.y = y
        self.width = width
        self.message = ""
        self.message_type = "info"  # info, success, error, warning
    
    def draw(self, stdscr):
        """Draw the status bar"""
        # Clear the line
        try:
            stdscr.addstr(self.y, self.x, " " * self.width)
        except curses.error:
            pass
        
        if self.message:
            # Choose color based on message type
            if self.message_type == "error":
                color_pair = curses.color_pair(5)  # Red
            elif self.message_type == "success":
                color_pair = curses.color_pair(2)  # Green
            elif self.message_type == "warning":
                color_pair = curses.color_pair(4)  # Yellow
            else:
                color_pair = curses.color_pair(3)  # Normal
            
            # Truncate message if too long
            display_message = self.message
            if len(display_message) > self.width:
                display_message = display_message[:self.width - 3] + "..."
            
            try:
                stdscr.addstr(self.y, self.x, display_message, color_pair)
            except curses.error:
                pass
    
    def set_message(self, message: str, message_type: str = "info"):
        """Set a status message"""
        self.message = message
        self.message_type = message_type
    
    def clear(self):
        """Clear the status message"""
        self.message = ""