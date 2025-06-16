# AI_TTRPG

## TODO

- [ ] Need to add a terminal command for dice roll. Currently the method for dice roll doesn't quite work. I needed to open a new terminal instance and do `random.randint(1,20)`.
- [ ] Need to add a terminal command for ending the game based on the current decisions. Just prompt Gemini API with "Conclude game based on prior decisions in an interesting way. I need to leave."
- [ ] Need to connect the game to a database so that the game can be paused and continued whenever the player wants. There should be an option called pause and then the entire conversation would be automatically saved to a database.
- [ ] Need to fix the logging. Even if the terminal runs out of display space the story should be easily exportable using the logs but they currently don't work as intended.
- [ ] There should be an option to export the overall story once the campaign ends as a PDF file. This would require reworking the parts which asked for choice and making them seamless with the next section and so on. This could be perfect for the long context prompt for Gemini.

## Usage

- Clone the repository:
  
```bash
git clone https://github.com/Aditya-1301/AI_TTRPG.git
cd AI_TTRPG/
```

- Go to Google AI Studio and create an API key and put it into an .env file in the same folder as the cloned repository (AI_TTRPG) like this:

```bash
GEMINI_API_KEY=YOUR_API_KEY
```

- Create a Virtual environment:

```bash
python3 -m venv venv
```

- Activate the Virtual Environment:

```bash
source venv/bin/activate
```

- Install Required Packages:

```bash
pip install -r requirements.txt
```

- Run the code:

```bash
python3 experiment.py
```

- Enjoy!

## CAUTION

Currently, this is not connected to a database so if you want to save the contents of the scenario then you should do this manually or you risk losing the story that you have generated for your self. Currently I am working on connecting this to some database so that the messages sent between the user and the chatbot can be saved for later, so that the user can pause and continue the session whenever they want.