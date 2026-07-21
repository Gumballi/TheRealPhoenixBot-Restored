import os
import json
import urllib.request
import urllib.parse

from telegram import Bot, Update, ParseMode
from telegram.ext import run_async

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

# This will fetch the API key from your Render environment variables
SIMKL_CLIENT_ID = os.environ.get("SIMKL_CLIENT_ID")

def search_simkl(bot: Bot, update: Update, args: list, media_type: str):
    msg = update.effective_message
    
    if not SIMKL_CLIENT_ID:
        msg.reply_text("The bot owner hasn't configured the Simkl API key yet!")
        return
        
    if not args:
        # Provide helpful examples depending on the command used
        if media_type == "anime":
            example = "/anime Jujutsu Kaisen"
        elif media_type == "tv":
            example = "/tv Invincible"
        else:
            example = "/movie The Matrix"
            
        msg.reply_text(f"Please provide a title!\nExample: `{example}`", parse_mode=ParseMode.MARKDOWN)
        return
        
    query = " ".join(args)
    bot.send_chat_action(chat_id=msg.chat_id, action="typing")
    
    try:
        # Simkl's v1 search endpoint
        url = f"https://api.simkl.com/search/{media_type}?q={urllib.parse.quote(query)}&client_id={SIMKL_CLIENT_ID}"
        req = urllib.request.Request(url, headers={'User-Agent': 'TheRealPhoenixBot/1.0'})
        
        # Bypass SSL Verification issues just like we did in extras.py
        import ssl
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=context, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if not data:
            msg.reply_text(f"Couldn't find any {media_type} matching '{query}'.")
            return
            
        # Grab the top result
        result = data[0]
        title = result.get('title', 'Unknown Title')
        year = result.get('year', 'Unknown Year')
        poster_id = result.get('poster')
        simkl_id = result.get('ids', {}).get('simkl')
        
        # Construct the caption
        link = f"https://simkl.com/{media_type}/{simkl_id}/" if simkl_id else "https://simkl.com/"
        caption = f"🎬 *{title}* ({year})\n\n[View details on Simkl]({link})"
        
        # Send the poster if it exists, otherwise just send the text
        if poster_id:
            poster_url = f"https://simkl.in/posters/{poster_id}_m.webp"
            msg.reply_photo(photo=poster_url, caption=caption, parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        print(f"[ERROR] Simkl {media_type} search failed: {e}")
        msg.reply_text("An error occurred while searching Simkl. Try again later!")


@run_async
def anime(bot: Bot, update: Update, args):
    search_simkl(bot, update, args, "anime")

@run_async
def tv(bot: Bot, update: Update, args):
    search_simkl(bot, update, args, "tv")

@run_async
def movie(bot: Bot, update: Update, args):
    search_simkl(bot, update, args, "movie")


__help__ = """
Look up information, posters, and links for your favorite shows!

*Available commands:*
 - /anime <title>: Search for anime details.
 - /tv <title>: Search for a TV show.
 - /movie <title>: Search for a movie.
"""

__mod_name__ = "Media Search"

# Register handlers
ANIME_HANDLER = DisableAbleCommandHandler("anime", anime, pass_args=True)
TV_HANDLER = DisableAbleCommandHandler("tv", tv, pass_args=True)
MOVIE_HANDLER = DisableAbleCommandHandler("movie", movie, pass_args=True)

dispatcher.add_handler(ANIME_HANDLER)
dispatcher.add_handler(TV_HANDLER)
dispatcher.add_handler(MOVIE_HANDLER)
