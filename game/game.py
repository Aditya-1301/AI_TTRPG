import os
import sys
import logging
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
import random
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# --- Supabase Client ---
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if not supabase_url or not supabase_key:
    raise ValueError("Please set your SUPABASE_URL and SUPABASE_KEY in the .env file")
supabase: Client = create_client(supabase_url, supabase_key)

# --- Logging Setup ---
def setup_application_logging(log_directory="logs"):
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_directory, f"game_log_{timestamp}.log")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.info(f"Logging application output to: {log_filename}")
    return logger

logger = setup_application_logging()

# --- Gemini API Client Setup ---
def setup_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not found in .env file.")
        raise ValueError("Please set your GEMINI_API_KEY in the .env file")
    client = genai.Client(api_key=api_key)
    logger.info("Gemini client setup successfully.")
    return client

# --- Generate Response Function ---
def generate_response(client, conversation_history, temperature=0.7):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20", # Your specified model
            contents=conversation_history,
            config=types.GenerateContentConfig(temperature=temperature)
        )
        logger.debug(f"Raw model response: {response.text}")
        return response.text
    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return None

# --- Supabase Functions ---
def create_new_session():
    try:
        response = supabase.table('sessions').insert({}).execute()
        if response.data:
            session_id = response.data[0]['id']
            session_uuid = response.data[0]['session_uuid']
            return session_id, session_uuid
        return None, None
    except Exception as e:
        logger.error(f"Error creating new session: {e}", exc_info=True)
        return None, None

def save_message(session_id, role, content):
    if not session_id: return
    try:
        supabase.table('messages').insert({'session_id': session_id, 'role': role, 'content': content}).execute()
    except Exception as e:
        logger.error(f"Error saving message: {e}", exc_info=True)

def load_session(session_uuid):
    try:
        session_response = supabase.table('sessions').select('id').eq('session_uuid', session_uuid).execute()
        if not session_response.data:
            print(f"Error: Session with UUID {session_uuid} not found.")
            return None, None, None
        session_id = session_response.data[0]['id']
        messages_response = supabase.table('messages').select('role, content').eq('session_id', session_id).order('created_at').execute()
        conversation_history = [types.Content(parts=[types.Part(text=msg['content'])], role=msg['role']) for msg in messages_response.data]
        # FIX #1: The function must return all three state variables.
        return session_id, session_uuid, conversation_history
    except Exception as e:
        logger.error(f"Error loading session: {e}", exc_info=True)
        return None, None, None

def reset_session_history(session_id):
    try:
        supabase.table('messages').delete().eq('session_id', session_id).execute()
        logger.info(f"Message history for session ID {session_id} has been cleared.")
        return True
    except Exception as e:
        logger.error(f"Error resetting session history: {e}", exc_info=True)
        return False
        
def print_help():
    print("""
Available Commands:
/new                     - Start a new game session.
/resume [session_uuid]   - Resume a saved game session.
/list                    - List all saved game session UUIDs.
/delete [session_uuid]   - Delete a game session (cannot be the active one).
/reset                   - Wipes and restarts the CURRENT game session.
/exit or /pause          - Exits the application.
/roll                    - Roll a D20 for a skill check.
/help                    - Displays this help message.
    """)

# --- Main Game Logic ---
def main():
    # Check for environment variable to auto-resume a session
    auto_resume_uuid = os.getenv('TTRPG_RESUME_SESSION')
    
    # Loop 1: The Restart Loop
    while True:
        client = setup_gemini_client()
        session_id = None
        session_uuid = None
        conversation_history = []
        
        # If auto-resume is set, try to load that session
        if auto_resume_uuid:
            print(f"Auto-resuming session: {auto_resume_uuid}")
            loaded_id, loaded_uuid, loaded_history = load_session(auto_resume_uuid)
            if loaded_id:
                session_id, session_uuid, conversation_history = loaded_id, loaded_uuid, loaded_history
                if conversation_history and conversation_history[-1].role == "model":
                    print("\n--- Session Resumed ---\nGM:")
                    print(conversation_history[-1].parts[0].text)
                # Clear the environment variable so it doesn't auto-resume again
                if 'TTRPG_RESUME_SESSION' in os.environ:
                    del os.environ['TTRPG_RESUME_SESSION']
                auto_resume_uuid = None
            else:
                print(f"Failed to load session {auto_resume_uuid}. Starting normally.")
                auto_resume_uuid = None
        
        # Loop 2: The Initialization Loop (only if not auto-resumed)
        if not session_id:
            print("\nWelcome to the AI TTRPG!")
            print("Type '/new' to start, '/resume [uuid]' to continue, '/list' to see saved games, or '/help' for all commands.")
            
            while True:
                initial_input = input("> ").strip()
                if not initial_input: continue

                cmd_parts = initial_input.lower().split(' ')
                cmd = cmd_parts[0]

                if cmd == '/new':
                    session_id, session_uuid = create_new_session()
                    if session_id:
                        print(f"Started a new game. Your session UUID is: {session_uuid}")
                        break
                elif cmd == '/resume':
                    try:
                        uuid_to_load = cmd_parts[1]
                        loaded_id, loaded_uuid, loaded_history = load_session(uuid_to_load)
                        if loaded_id:
                            session_id, session_uuid, conversation_history = loaded_id, loaded_uuid, loaded_history
                            if conversation_history and conversation_history[-1].role == "model":
                                print("\n--- Session Resumed ---\nGM:")
                                print(conversation_history[-1].parts[0].text)
                            break
                    except IndexError:
                        print("Usage: /resume [session_uuid]")
                elif cmd == '/list':
                    response = supabase.table('sessions').select('session_uuid, created_at').execute()
                    if response.data:
                        print("\n--- Saved Sessions ---")
                        for s in response.data:
                            print(f"UUID: {s['session_uuid']} (Created: {s['created_at']})")
                    else:
                        print("No saved sessions found.")
                elif cmd == '/help':
                    print_help()
                elif cmd in ['/exit', '/pause']:
                    print("Exiting application.")
                    return
                else:
                    print("Invalid command. Please type '/new', '/resume [uuid]', '/list', or '/help'.")
        
        # --- Stage 2: Main Game Loop ---
        gm_persona_instruction = """
        You are an advanced AI Game Master (GM) for an immersive Dungeons & Dragons-style Tabletop Role-Playing Game. Your primary goal is to facilitate an engaging, dynamic, and narrative-rich experience for the player(s).

        1. GM Persona & Core Principles:
            - Role: You are the omniscient GM. You describe the world, its inhabitants, and the consequences of player actions. You interpret rules, adjudicate outcomes, and drive the evolving narrative.
            - Tone & Style: Your narrative is vivid, descriptive, and immersive, akin to a well-written fantasy novel. Employ rich sensory details, strong verbs, and evocative language. Maintain a consistent tone and atmosphere appropriate to the scenario.
            - Player Agency: Player choices are paramount. Always adapt the story meaningfully to their actions, even if unexpected. Avoid railroading.
            - Fairness: Adjudicate rules impartially.
            - Conciseness & Flow: Deliver narrative turns in single, comprehensive messages.
        2. Game Setup & Initialization (Initial Turn Directives):
            - Scenario Generation:
                - IF user provides setting/genre/mood via additional prompts: Integrate these seamlessly into the scenario.
                - IF user provides initial images: Analyze the images for visual cues (atmosphere, objects, characters) and weave them directly into the opening scene, setting, and mood.
                - OTHERWISE: Invent a compelling fantasy scenario, starting location, and initial hook for the player(s).
            - Character Initialization:
                - IF player(s) provide character sheets (Name, Class, Stats, Inventory): Incorporate these directly into the game state. Display these initial details clearly to the player(s).
            - OTHERWISE (AI Generation):
                - For 1 Player:
                    - Define a unique Player Character (PC): Name, Class, Starting Statistics, basic Inventory, and a brief background. Present these to the player.
                    - Generate a small, cohesive AI-Controlled Party (NPCs): For each, define Name, Class, Core Statistics, distinct Personality Traits, unique Voice/Dialogue Style, and simple Motivations. These companions will react and act based on the PC's choices.
            - For Multiple Players: Define a unique PC (Name, Class, Starting Statistics, basic Inventory) for each human player if not provided. Present these to the respective players.
                - Character Consistency: Remember that all character information (PC and NPC stats, inventory, etc.) is provided to you by the application in a structured format before each turn. Always refer to this authoritative data and ensure character details remain consistent throughout the campaign.
                - Initial Game Rules & Systems: As your first message to the player(s), clearly outline the core game rules, combat/magic systems, and turn structure for this adventure.
                - Combat: Specify if combat is Turn-Based or Narrative-Flowing (Real-Time).
                - Turn-Based: Explain initiative (if applicable), actions, and reactions.
                - Narrative-Flowing: Describe how combat actions integrate directly into the narrative description, with skill checks dictating success/failure.
                - Magic: Explain how spells/abilities work within this scenario, how they affect the world, and how players can attempt to use them.
                - Skill Checks: Explain that dice rolls determine success, and how you will request them.
                - Rule Penalties: Clearly state that rules exists for a reason. Clever circumvention that enhances the narrative or comedy may be allowed once as an exception, but repeated or uninspired attempts to bypass rules will result in in-game penalties or consequences.
                - First Turn Output: Describe the initial scenario in detail, introduce the characters (PCs and AI companions), and then prompt the player for their first action.
    3. Core Game Loop & Turn Structure:
        - Comprehensive Turn Narrative (GM Output):
        - Each of your responses will be a single, cohesive, long narrative block.
        - This block must include: Scene description (sights, sounds, mood), narration of events, actions of all NPCs (including AI companions), and all dialogue.
        - NPC Dialogue Format: "Character Name: 'Dialogue here.'"
        - Dynamic NPC Spotlight: When narratively appropriate, allow an AI-controlled companion or other NPC to take a more prominent role in the narrative or dialogue.
        - Call to Action: Conclude your narrative message with a clear prompt for the player's next action(s): "What do you do next?" or "How do you proceed?"
        - Skill Check Adjudication:
        - IF a player's proposed action requires a check: State: "You attempt to [action]. Please roll a [Skill Name] check."
        - DO NOT roll dice yourself. Wait for the application to provide the dice roll result.
        - Upon receiving dice roll results: Incorporate the [SKILL_CHECK_RESULT] and [UPDATED_PLAYER_STATS] (provided by the application) into your narrative. First, acknowledge the roll's outcome, then describe its direct impact on the scenario and characters, including any relevant dialogue.
    4. Multimodal Integration (Image Handling):
        - Image Input by Player: When a player provides an image, carefully analyze its content and integrate it into the narrative.
        - Interpretation: Understand the image's context (e.g., character description, item, action, environment) and how it informs the player's intent.
        - Integration: Weave the visual information into your descriptive text, NPC reactions, or consequences.
    5. Context & Campaign Management:
        - Context Awareness: Be aware of the game's overall memory capacity (provided by the application backend).
        - Dynamic Pacing:
        - IF alerted by the application of approaching context limits: Begin subtly guiding the current scenario towards a conclusion or a natural breaking point. Introduce climactic elements or clear objectives to facilitate wrapping up the current narrative arc.
        - Player Choice Override: Even when pacing for a conclusion, player choices still determine the path. Adapt if they divert the narrative.
        - Emergent Narrative: Players' choices always directly alter the scenario. The story is a collaborative, evolving creation.
    6. Social Dynamics & Emergent Gameplay:
        - Opportunities for Interaction: Actively look for chances to introduce:
        - Banter: Between PCs and AI companions, or between PCs themselves. Make it natural and character-driven.
        - Alliances/Rivalries: Introduce situations where players (or PCs and NPCs) might naturally form bonds or conflicts based on shared goals, opposing views, or personality clashes. These must emerge organically from the scenario and character interactions, not be shoehorned in.
        - Player-Driven Social Outcomes: Observe player interactions and tailor NPC responses or narrative events to either foster cooperation or escalate conflict, as appropriate for the evolving story.
    7. Safety & Content Moderation:
        - Strict Guidelines: Never generate content that is explicit, hateful, discriminatory, dangerous, or promotes self-harm. Maintain a respectful and inclusive environment.
        - User Boundaries: If a player expresses a boundary or discomfort, respect it immediately and adjust the narrative.
        - Remember: Your main goal is to be an engaging, adaptive, and consistent GM. You are the eyes, ears, and voice of the world and its inhabitants.
        """

        if not conversation_history:
            initial_prompt = (gm_persona_instruction + 
                              "\n\nIMPORTANT: Your first task is to greet me and ask two questions. "
                              "First, ask if I have a specific scenario in mind or if you should create one. "
                              "Second, ask if I want to define my character or if you should create one for me. "
                              "Do not generate a story, characters, or rules until I have answered.")
            
            conversation_history.append(types.Content(parts=[types.Part(text=initial_prompt)], role="user"))
            save_message(session_id, 'user', initial_prompt)
            logger.info("Initial GM persona and starting instruction prepared for the model.")
            
            initial_gm_response = generate_response(client, conversation_history)
            if initial_gm_response:
                print("\n---------------------------------------------------\nGM:")
                print(initial_gm_response)
                conversation_history.append(types.Content(parts=[types.Part(text=initial_gm_response)], role="model"))
                save_message(session_id, 'model', initial_gm_response)
            else:
                logger.error("Failed to get initial GM response. Exiting application.")
                return

        # Loop 3: The Main Gameplay Loop
        restart_game = False
        while True:
            print("\n\nYour Turn:")
            user_input = input("> ").strip()
            
            if not user_input: continue

            is_game_action = True
            cmd_parts = user_input.lower().split(' ')
            cmd = cmd_parts[0]

            if cmd.startswith('/'):
                is_game_action = False
                
                if cmd in ['/exit', '/pause']:
                    print(f"Game paused. To resume, restart the script and use:\n/resume {session_uuid}")
                    return
                elif cmd == '/new':
                    print("Restarting to create a new game...")
                    restart_game = True
                    break
                elif cmd == '/resume':
                    try:
                        uuid_to_load = cmd_parts[1]
                        if uuid_to_load == session_uuid:
                            print("You are already in that session.")
                        else:
                            print(f"Attempting to resume session {uuid_to_load}...")
                            loaded_id, loaded_uuid, loaded_history = load_session(uuid_to_load)
                            if loaded_id:
                                session_id, session_uuid, conversation_history = loaded_id, loaded_uuid, loaded_history
                                if conversation_history and conversation_history[-1].role == "model":
                                    print("\n--- Session Resumed ---\nGM:")
                                    print(conversation_history[-1].parts[0].text)
                    except IndexError:
                        print("Usage: /resume [session_uuid]")
                elif cmd == '/help':
                    print_help()
                elif cmd == '/list':
                    response = supabase.table('sessions').select('session_uuid, created_at').execute()
                    if response.data:
                        print("\n--- Saved Sessions ---")
                        for s in response.data:
                            print(f"UUID: {s['session_uuid']} (Created: {s['created_at']})")
                    else:
                        print("No saved sessions found.")
                elif cmd == '/delete':
                    try:
                        uuid_to_delete = cmd_parts[1]
                        if uuid_to_delete == session_uuid:
                            print("Cannot delete the active session. Use /new or /exit first.")
                        else:
                            # FIX #3: Add confirmation prompt
                            if input(f"Are you sure you want to permanently delete session {uuid_to_delete}? (y/n) > ").lower() == 'y':
                                # FIX #2: Implement the actual delete call
                                supabase.table('sessions').delete().eq('session_uuid', uuid_to_delete).execute()
                                print(f"Session {uuid_to_delete} has been deleted.")
                            else:
                                print("Deletion cancelled.")
                    except IndexError:
                        print("Usage: /delete [session_uuid]")
                elif cmd == '/reset':
                    if input(f"Are you sure you want to reset all history for session {session_uuid}? (y/n) > ").lower() == 'y':
                        if reset_session_history(session_id):
                            conversation_history = []
                            print("Session has been reset.")
                            user_input = (gm_persona_instruction + 
                                          "\n\nIMPORTANT: The session has been reset. Greet me again and ask me what I want to do.")
                            is_game_action = True
                        else:
                            print("Error: Could not reset session history.")
                    else:
                        print("Reset cancelled.")
                elif cmd == '/roll':
                    dice_roll = random.randint(1, 20)
                    print(f"You rolled a D20 and got a {dice_roll}.")
                    user_input = f"I rolled a D20 and got a {dice_roll}. What happens?"
                    is_game_action = True
                else:
                    print("Unknown command. Type /help for a list of commands.")

            if is_game_action:
                logger.info(f"USER_INPUT_TO_GM: {user_input}")
                conversation_history.append(types.Content(parts=[types.Part(text=user_input)], role="user"))
                save_message(session_id, 'user', user_input)

                gm_response = generate_response(client, conversation_history)
                if gm_response:
                    print("\n---------------------------------------------------\nGM:")
                    print(gm_response)
                    conversation_history.append(types.Content(parts=[types.Part(text=gm_response)], role="model"))
                    save_message(session_id, 'model', gm_response)
                else:
                    logger.error("Failed to get GM response. Your turn was not saved. Please try again.")
                    conversation_history.pop()

        if not restart_game:
            break

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        logger.info("\nProgram interrupted by user. Exiting gracefully.")
    except Exception as e:
        logger.critical(f"\nAn unexpected critical error occurred: {e}", exc_info=True)
    finally:
        logger.info("Game session ended.")
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)