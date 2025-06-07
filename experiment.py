import os
import sys
import logging
import datetime
from google import genai
from google.genai import types # Crucial for Content and Part types
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# --- Logging Setup ---
def setup_application_logging(log_directory="logs"):
    """
    Sets up Python's logging module to output to both console and a file.
    """
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_directory, f"game_log_{timestamp}.log")

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Keep root logger at INFO to capture all desired messages for file

    # Prevent adding handlers multiple times if function is called more than once
    if not logger.handlers:
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Create a console handler (for terminal output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING) # Only warnings/errors/critical to terminal
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Create a file handler (for file output)
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.INFO) # Remains INFO for comprehensive file logging
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info(f"Logging application output to: {log_filename}")
    return logger

# Get the logger instance globally
logger = setup_application_logging()

# --- Gemini API Client Setup ---
def setup_gemini_client():
    """Retrieves the API key and initializes the Gemini client."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not found in .env file.")
        raise ValueError("Please set your GEMINI_API_KEY in the .env file")
    client = genai.Client(api_key=api_key)
    logger.info("Gemini client setup successfully.")
    return client

# --- Generate Response Function ---
def generate_response(client, conversation_history, temperature=0.7):
    """
    Generates a response from the Gemini model based on the conversation history.

    Args:
        client: The initialized Gemini client.
        conversation_history (list): A list of types.Content objects representing the conversation.
        temperature (float): Controls the randomness of the output. Higher values
                             mean more random, lower values mean more deterministic.

    Returns:
        str: The generated text response from the model, or None if an error occurs.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20", # Your specified model
            contents=conversation_history,
            config=types.GenerateContentConfig(temperature=temperature)
        )
        logger.debug(f"Raw model response: {response.text}") # Log raw response for debugging
        return response.text
    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True) # Log traceback
        return None

# --- Main Game Logic ---
def main():
    try:
        client = setup_gemini_client()
        
        # Define the GM persona/system instruction.
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
        
        # Initial conversation history. The first "user" message provides the system instruction/GM persona.
        conversation_history = [
            types.Content(
                parts=[types.Part(text=gm_persona_instruction + "\n\nAsk me for the initial scenario and if I would like to define a character or any other details. " 
                                  + " If I say you can define either of them then proceed to define them and start the adventure.")],
                role="user"
            ),
        ]
        logger.info("Initial GM persona and starting instruction prepared for the model.")

        # Generate the initial GM response
        initial_gm_response = generate_response(client, conversation_history)
        
        if initial_gm_response:
            # Print to terminal without logging prefixes
            print("\n---------------------------------------------------\nGM:")
            print(initial_gm_response)
            # Log the full response content to the file
            logger.info(f"GM: {initial_gm_response}")
            # Add the GM's initial response to the conversation history
            conversation_history.append(types.Content(parts=[types.Part(text=initial_gm_response)], role="model"))
        else:
            logger.error("Failed to get initial GM response. Exiting application.") # Error still goes to terminal and file
            return # Exit if initial response fails

        # The main game loop
        while True:
            print("\n---------------------------------------------------\n\nYour Turn:") # Direct print to terminal
            user_input = str(input()) # input() reads from terminal, not captured by logger directly

            # Log the user's actual input (only to file)
            logger.info(f"USER: {user_input}") # Log user input to file
            
            # Handle "Dice Roll" command
            if user_input.lower() == "dice roll":
                dice_roll = random.randint(1, 20)
                logger.info(f"Player requested a dice roll. Result: {dice_roll}") # Only goes to file
                # Append the dice roll result as part of the user's turn for the model
                conversation_history.append(types.Content(parts=[types.Part(text=f"\nI rolled a D20 and got a {dice_roll}. How does this affect my action?\n")], role="user"))
            else:
                # Add the user's normal response to the conversation history
                conversation_history.append(types.Content(parts=[types.Part(text=user_input)], role="user"))
            
            # Generate the new GM response based on the updated conversation history
            current_gm_response = generate_response(client, conversation_history)
            
            if current_gm_response:
                # Print to terminal without logging prefixes
                print("\n---------------------------------------------------\nGM:")
                print(current_gm_response)
                # Log the full response content to the file
                logger.info(f"GM: {current_gm_response}")
                # Add the GM's current response to the conversation history
                conversation_history.append(types.Content(parts=[types.Part(text=current_gm_response)], role="model"))
            else:
                logger.error("Failed to get GM response for current turn. Continuing loop.") # Error still goes to terminal and file
                # You might want to add more robust error handling here, e.g., retry or exit.
            
    except ValueError as ve:
        logger.critical(f"Configuration Error: {ve}")
    except KeyboardInterrupt:
        logger.info("Program interrupted by user (Ctrl+C). Exiting gracefully.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True) # Log traceback for unexpected errors
    finally:
        logger.info("Game session ended. Closing log handlers.")
        # Ensure all logging handlers are closed to prevent resource leaks
        # Iterate over a copy of the list because handlers might be removed during iteration
        for handler in logger.handlers[:]: 
            handler.close()
            logger.removeHandler(handler)

if __name__ == "__main__":
    main()