import threading
import asyncio
import random
import os
import logging
from flask import Flask, jsonify, render_template

app = Flask(
    __name__,
    static_folder="static",     # where PNGs (happy.png, sad.png, etc.) can go
    template_folder="templates" # where HTML templates go
)

###############################################################################
# Global State
###############################################################################
current_emotion = "happy"  # "happy", "sad", "angry", etc.
is_talking = False

# We'll keep a reference to a "revert to happy" timer (async Task) if scheduled
revert_timer_task = None
REVERT_DELAY_SECONDS = 3  # How many seconds after idle to force revert to "happy"

###############################################################################
# Revert Timer Logic (Server-Side)
###############################################################################
async def _revert_after_delay(seconds: float):
    """
    Wait 'seconds' while the avatar is idle (talking=False).
    If still not talking at the end, and not already happy, revert to "happy".
    """
    await asyncio.sleep(seconds)
    # Double-check we're still idle
    if not is_talking and current_emotion != "happy":
        set_avatar_state(emotion="happy")

def _schedule_revert_to_happy(seconds: float):
    """
    Cancel any existing revert timer, then schedule a new one.
    """
    global revert_timer_task
    # Cancel old task if exists
    if revert_timer_task and not revert_timer_task.done():
        revert_timer_task.cancel()
    # Create new task
    loop = asyncio.get_event_loop()
    revert_timer_task = loop.create_task(_revert_after_delay(seconds))


###############################################################################
# Public Function Called by main.py
###############################################################################
def set_avatar_state(emotion=None, talking=None):
    """
    Called by main.py to update the avatar's emotion or talking state.
    """
    global current_emotion, is_talking

    old_emotion = current_emotion
    old_talking = is_talking

    if emotion is not None:
        current_emotion = emotion
    if talking is not None:
        is_talking = talking

    # If we just switched from talking=True -> talking=False
    if old_talking and not is_talking:
        # If the new emotion is not "happy", schedule a revert
        if current_emotion != "happy":
            _schedule_revert_to_happy(REVERT_DELAY_SECONDS)
        # Otherwise, do nothing (already happy)
    
    # If we just switched from talking=False -> talking=True,
    # or changed emotion while talking => cancel any pending revert
    if is_talking:
        # Cancel revert timer if it exists
        global revert_timer_task
        if revert_timer_task and not revert_timer_task.done():
            revert_timer_task.cancel()
            revert_timer_task = None


###############################################################################
# Flask Routes
###############################################################################
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    return {
        "emotion": current_emotion,
        "talking": is_talking
    }

###############################################################################
# Run Flask without dev logs
###############################################################################
def _run_flask():
    # Disable flask/werkzeug logs
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    # Run the server
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

async def run_avatar_server():
    """
    Called by main.py in an async task.
    Spawns a thread to run the Flask webserver.
    """
    thread = threading.Thread(target=_run_flask, daemon=True)
    thread.start()
    await asyncio.sleep(0)  # yield so the thread can start
