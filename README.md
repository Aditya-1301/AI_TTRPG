# AI_TTRPG

## TODO

- [x] Need to add a terminal command for dice roll. Currently the method for dice roll doesn't quite work. I needed to open a new terminal instance and do `random.randint(1,20)`.
- [x] Need to connect the game to a database so that the game can be paused and continued whenever the player wants. There should be an option called pause and then the entire conversation would be automatically saved to a database.
- [ ] Need to add a terminal command for ending the game based on the current decisions. Just prompt Gemini API with "Conclude game based on prior decisions in an interesting way. I need to leave."
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

- Go to Supabase and create a new project and run the following SQL queries in the editor to create the "messages" and "sessions" tables:


```SQL
CREATE TABLE sessions (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_uuid UUID DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
```

```SQL
CREATE TABLE messages (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
```

Get the URL and KEY for the project and put them into .env file:

```bash
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_API_KEY
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
python3 experiment2.py
```

- Enjoy!