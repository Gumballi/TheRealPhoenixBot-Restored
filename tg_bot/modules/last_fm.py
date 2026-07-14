# Last.fm module by @TheRealPhoenix - https://github.com/rsktg
import requests

from telegram import Bot, Update, Message, Chat, ParseMode
from telegram.ext import run_async, CommandHandler

from tg_bot import dispatcher, LASTFM_API_KEY
from tg_bot.modules.disable import DisableAbleCommandHandler

import tg_bot.modules.sql.last_fm_sql as sql


@run_async
def set_user(bot: Bot, update: Update, args):
    msg = update.effective_message
    if args:
        user = update.effective_user.id
        username = " ".join(args).strip()
        sql.set_user(user, username)
        msg.reply_text(f"Username set as {username}!")
    else:
        msg.reply_text("That's not how this works...\nRun /setuser followed by your username!")
        

@run_async
def clear_user(bot: Bot, update: Update):
    user = update.effective_user.id
    sql.set_user(user, "")
    update.effective_message.reply_text("Last.fm username successfully cleared from my database!")
    
  
@run_async
def last_fm(bot: Bot, update: Update):
    msg = update.effective_message
    user = update.effective_user.first_name
    user_id = update.effective_user.id
    username = sql.get_user(user_id)
    if not username:
        msg.reply_text("You haven't set your username yet! Use /setuser <username>")
        return
    
    base_url = "http://ws.audioscrobbler.com/2.0"
    
    try:
        res = requests.get(
            f"{base_url}?method=user.getrecenttracks&limit=3&extended=1&user={username}&api_key={LASTFM_API_KEY}&format=json",
            timeout=8
        )
        if res.status_code != 200:
            msg.reply_text("Hmm... something went wrong.\nPlease ensure that you've set the correct username!")
            return
            
        data = res.json()
        recent_tracks = data.get("recenttracks")
        if not recent_tracks:
            msg.reply_text("Could not retrieve recent tracks. Check your username.")
            return
            
        tracks = recent_tracks.get("track")
        if not tracks:
            msg.reply_text("You don't seem to have scrobbled any songs...")
            return
            
        # If it's a single track returned as a dict instead of a list
        if isinstance(tracks, dict):
            tracks = [tracks]
            
        first_track = tracks[0]
        is_now_playing = False
        
        # Check if the song is currently playing
        attr = first_track.get("@attr")
        if attr and attr.get("nowplaying") == "true":
            is_now_playing = True

        if is_now_playing:
            # Safe Image handling
            images = first_track.get("image", [])
            image = images[3].get("#text") if len(images) > 3 else ""
            
            artist = first_track.get("artist", {}).get("name", "Unknown Artist")
            song = first_track.get("name", "Unknown Song")
            
            try:
                loved = int(first_track.get("loved", 0))
            except (ValueError, TypeError):
                loved = 0
                
            rep = f"{user} is currently listening to:\n"
            if not loved:
                rep += f"🎧  <code>{artist} - {song}</code>"
            else:
                rep += f"🎧  <code>{artist} - {song}</code> (♥️, loved)"
                
            # Embed image invisibly so Telegram displays it as a preview
            if image:
                rep += f"<a href='{image}'>\u200c</a>"
        else:
            # Fixed: Use a list of tuples to allow multiple songs by the same artist
            track_list = []
            for t in tracks[:3]: # Safe limit up to 3 tracks (won't crash if they have only 1 or 2)
                t_artist = t.get("artist", {}).get("name", "Unknown Artist")
                t_song = t.get("name", "Unknown Song")
                track_list.append((t_artist, t_song))
                
            rep = f"{user} was listening to:\n"
            for artist, song in track_list:
                rep += f"🎧  <code>{artist} - {song}</code>\n"
                
            # Fetch total scrobbles
            user_info_res = requests.get(
                f"{base_url}?method=user.getinfo&user={username}&api_key={LASTFM_API_KEY}&format=json",
                timeout=8
            )
            if user_info_res.status_code == 200:
                last_user = user_info_res.json().get("user", {})
                scrobbles = last_user.get("playcount", "0")
                rep += f"\n(<code>{scrobbles}</code> scrobbles so far)"
        
        msg.reply_text(rep, parse_mode=ParseMode.HTML)
        
    except requests.exceptions.RequestException:
        msg.reply_text("Could not connect to Last.fm. Try again later!")
    except Exception as e:
        msg.reply_text("An error occurred while parsing your track data.")


__help__ = """
Share what you're listening to with the help of this module!

*Available commands:*
 - /setuser <username>: sets your last.fm username.
 - /clearuser: removes your last.fm username from the bot's database.
 - /lastfm: returns what you're scrobbling on last.fm.
"""

__mod_name__ = "Last.FM"


SET_USER_HANDLER = CommandHandler("setuser", set_user, pass_args=True)
CLEAR_USER_HANDLER = CommandHandler("clearuser", clear_user)
LASTFM_HANDLER = DisableAbleCommandHandler("lastfm", last_fm)

dispatcher.add_handler(SET_USER_HANDLER)
dispatcher.add_handler(CLEAR_USER_HANDLER)
dispatcher.add_handler(LASTFM_HANDLER)
