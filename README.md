# AI Twitch Chatbot – Quick Setup

This application is bundled as an **.exe**, so you **do not** need to install Python or additional dependencies. Simply follow the steps below to configure and run the chatbot.

---

## 1. Configuration Files

1. **`SECRETS.json`**  
   - Stores **Twitch** credentials (`client_id`, `client_secret`, `oauth_token`) and **OpenAI** token.  
   - Example structure:
     ```json
     {
       "openAI": { "authToken": "YOUR_OPENAI_KEY" },
       "twitch": {
         "client_id": "YOUR_TWITCH_CLIENT_ID",
         "client_secret": "YOUR_TWITCH_CLIENT_SECRET",
         "oauth_token": ""
       }
     }
     ```
   - If `oauth_token` is blank, the program will automatically retrieve and save a new token.

2. **`config.json`**  
   - Defines **channel name**, GPT model, voice settings, etc.  
   - Example:
     ```json
     {
       "twitch": {
         "channel_name": "YourTwitchName"
       },
       "gpt": {
         "ai_name": "YourBotName",
         "model": "gpt-4o-mini-2024-07-18",
         "max_tokens": 50
       },
       "voice": {
         "mode": "openai"
       },
       "paths": {
         "output_dir": "output",
         "blacklist": "blacklist.txt",
         "prompt": "gpt-prompt.txt"
       }
     }
     ```

3. **`gpt-prompt.txt`**  
   - Contains the **system-level prompt** for the GPT API (the “personality” or style).

4. **`blacklist.txt`**  
   - Names listed here (one per line) will be **ignored** by the AI.  
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
2. **Edit** `SECRETS.json` with your **Twitch** and **OpenAI** credentials.  
3. **Update** `config.json` with your Twitch channel name, AI name, etc.  
4. **Customize** `gpt-prompt.txt` if you want a different “system” prompt or style.  
5. **Run** `AI_Chatbot.exe`.  
6. In your streaming software (OBS, etc.):  
   - Add a **Browser Source** pointing to `http://127.0.0.1:5000` for the avatar animation.  
   - Configure your audio to capture the **TTS** output.

---

## 4. Notes

- The **chatbot** will only respond to messages that contain its **AI name** (from `config.json` → `"ai_name"`).  
- You can modify or replace sprites in **`static/`** and adjust the HTML/CSS/JS in **`templates/index.html`**.  
- **blacklist.txt** can be updated on the fly to ignore specific users without restarting.  
- If `oauth_token` in `SECRETS.json` is empty, the bot will request a new token from Twitch automatically.

---

**Enjoy your interactive Twitch Chat AI!**
