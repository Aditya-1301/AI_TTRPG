# AI_TTRPG

An AI-powered Tabletop Role-Playing Game (TTRPG) system using Google's Gemini AI as the Game Master, with session persistence via Supabase.

## Features

- **AI Game Master**: Powered by Google's Gemini AI for dynamic storytelling
- **Session Management**: Save and resume game sessions with full conversation history
- **Terminal UI**: WhatsApp-inspired session manager for easy navigation
- **Database Integration**: Persistent storage using Supabase
- **Dice Rolling**: Built-in D20 dice rolling system
- **Multiple Sessions**: Create and manage multiple campaign sessions

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Aditya-1301/AI_TTRPG.git
   cd AI_TTRPG/
   ```

2. **Set up environment variables:**
   Create a `.env` file in the project root with:
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

3. **Get your API keys:**
   - **Gemini API**: Go to [Google AI Studio](https://aistudio.google.com/) and create an API key
   - **Supabase**: Create a new project at [Supabase](https://supabase.com/) and get your URL and anon key

4. **Set up the database:**
   In your Supabase SQL editor, run these queries:
   ```sql
   CREATE TABLE sessions (
       id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
       session_uuid UUID DEFAULT gen_random_uuid() NOT NULL,
       created_at TIMESTAMPTZ DEFAULT now() NOT NULL
   );

   CREATE TABLE messages (
       id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
       session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
       role TEXT NOT NULL,
       content TEXT NOT NULL,
       created_at TIMESTAMPTZ DEFAULT now() NOT NULL
   );
   ```

5. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

6. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Option 1: Session Manager UI (Recommended)
Launch the terminal-based session manager:
```bash
python3 launch_ui.py
```

**UI Controls:**
- `↑↓`: Navigate between sessions
- `Enter`: Select/view session details
- `N`: Create new session
- `D`: Delete session (with confirmation)
- `R`: Refresh session list
- `Q`: Quit application

### Option 2: Direct Game Launch
Run the game directly:
```bash
python3 game/game.py
```

## Game Commands

During gameplay, you can use these commands:

- `/new` - Start a new game session
- `/resume [session_uuid]` - Resume a saved session
- `/list` - List all saved sessions
- `/delete [session_uuid]` - Delete a session
- `/reset` - Reset current session history
- `/roll` - Roll a D20 dice
- `/help` - Show all commands
- `/exit` or `/pause` - Exit the game

## Project Structure

```
AI_TTRPG/
├── game/
│   └── game.py              # Main game logic and AI GM
├── ui/
│   ├── session_manager.py   # Terminal UI for session management
│   ├── components.py        # UI components (TextBox, Button, etc.)
│   └── game_launcher.py     # Game launching utilities
├── starting_scenario_prompts/
│   └── dredge.txt          # Example scenario prompt
├── logs/                   # Game logs (auto-generated)
├── launch_ui.py           # UI launcher script
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .env                  # Environment variables (create this)
```

## Features in Detail

### AI Game Master
- Uses Google's Gemini 2.5 Flash model for intelligent responses
- Maintains character consistency and narrative flow
- Supports custom scenarios and character creation
- Handles dice rolls and skill checks

### Session Management
- Automatic session saving to Supabase database
- Resume any session from where you left off
- View session history and message counts
- Delete unwanted sessions

### Terminal UI
- Clean, intuitive interface inspired by WhatsApp
- Color-coded session status (active/inactive)
- Session previews with last messages
- Keyboard navigation and shortcuts

## TODO

- [ ] Add terminal command for concluding games intelligently
- [ ] Improve logging system for better story export
- [ ] PDF export functionality for completed campaigns
- [ ] Enhanced character sheet management
- [ ] Custom scenario templates

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source. Please check the license file for details.