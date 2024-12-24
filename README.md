# msvosch AI Twitch Chatbot – Quick Setup

This application is bundled as an **.exe**, so you **do not** need to install Python or additional dependencies. Simply click on "Releases" on the right sidebar and download the latest ZIP file. Then follow the steps below to configure and run the chatbot.

---

## 1. Configuration Files
In order to connect to the necessary services, you need to specify some information inside the `SECRETS.json` and `config.json` files.

**NOTE: DO NOT EVER SHARE OR DISPLAY THE INFORMATION INSIDE SECRETS.JSON**

1. **`SECRETS.json`**  
   - You will need to retrieve your openAI and/or Elevenlabs API tokens, depending on which TTS service you want to use. You will also need your Twitch Client ID and Secret in order to retrieve the stream title and current category. The OAuth token will be automatically generated for you.
   - Please use the following links for information on how to get these tokens
      - https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key
      - https://elevenlabs.io/app/home
         - After signing up, click your name in the bottom left and choose "API Keys"   
      - https://dev.twitch.tv/console/apps
         - Register a new application
         - Use http://localhost for the OAuth Redirect URLs
   - Example structure:
     ```json
     {
        "openAI": {
          "authToken": "TOKEN_HERE"
        },
        "elevenlabs": {
          "authToken": "TOKEN_HERE"
        },
        "twitch": {
          "client_id": "TOKEN_HERE",
          "client_secret": "TOKEN_HERE",
          "oauth_token": "WILL AUTO GENERATE ON FIRST USE"
        }
      }
     ```
   - If `oauth_token` is blank, the program will automatically retrieve and save a new token.

2. **`config.json`**  
   - Defines **channel name**, GPT model, voice settings, etc.
   - This will normally be configured by default, but you may change any settings you wish in here.
   - Example:
     ```json
      {
          "twitch": {
              "channel_name": ""
          },
          "voice": {
              "mode": "elevenlabs",
              "elevenlabs": {
                  "voice_id": "",
                  "model_id": "eleven_multilingual_v2",
                  "output_format": "mp3_44100_128",
                  "stability":"0.6",
                  "similarity_boost":"0.99",
                  "style":"0.3",
                  "use_speaker_boost":"True"
              },
              "openai": {
                  "model": "tts-1",
                  "voice": "shimmer"
              }
          },
          "gpt": {
              "ai_name": "Victoria", 
              "model": "gpt-4o-mini-2024-07-18",
              "max_tokens": 80
          },
          "paths": {
              "output_dir": "output",
              "blacklist": "blacklist.txt",
              "logs": "gpt.log",
              "prompt": "gpt-prompt.txt"
          }
      }
     ```

3. **`gpt-prompt.txt`**  
   - Contains the **system-level prompt** for the GPT API (the “personality” or style).
   - Use this file to personalize the AI with how you want it to responde.

4. **`blacklist.txt`**  
   - Twitch usernames listed here (one per line) will be **ignored** by the AI.  
   - This file can be edited at **runtime** without restarting the bot.

---

## 2. Folder Structure

```bash
AI_Chatbot.exe
SECRETS.json
config.json
gpt-prompt.txt
blacklist.txt
static/
├── happy.png
├── sad.png
├── blink.png
└── ...
templates/
└── index.html
...
```
## 3. Usage

1. **Place** all files in the same folder as `AI_Chatbot.exe`.  
2. **Edit** `SECRETS.json` with your credentials.  
3. **Update** `config.json` with your Twitch channel name, AI name, etc.  
4. **Customize** `gpt-prompt.txt` if you want a different “system” prompt or style.  
5. **Run** `AI_Chatbot.exe`.  
6. In your streaming software (OBS, etc.):  
   - Add a **Browser Source** pointing to `http://localhost:5000` for the avatar animation.
   - Set the resolution to 512px x 512px
   - Remove anything in the Custom CSS field.
   - Check "Refresh browser when scene becomes active"

---

## 4. Notes

- The **chatbot** will only respond to messages that contain its **AI name** (from `config.json` → `"ai_name"`).  
- You can modify or replace sprites in **`static/`** and adjust the HTML/CSS/JS in **`templates/index.html`**.  
- **blacklist.txt** can be updated on the fly to ignore specific users without restarting.  
- If `oauth_token` in `SECRETS.json` is empty, the bot will request a new token from Twitch automatically.

---

**Enjoy your interactive Twitch Chat AI!**
