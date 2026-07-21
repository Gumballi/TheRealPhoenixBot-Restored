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
        import ssl
        context = ssl._create_unverified_context()
        
        # Step 1: Search for the title
        search_url = f"https://api.simkl.com/search/{media_type}?q={urllib.parse.quote(query)}&client_id={SIMKL_CLIENT_ID}"
        search_req = urllib.request.Request(search_url, headers={'User-Agent': 'TheRealPhoenixBot/1.0'})
        
        with urllib.request.urlopen(search_req, context=context, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if not data:
            msg.reply_text(f"Couldn't find any {media_type} matching '{query}'.")
            return
            
        # Get the ID of the top result
        simkl_id = data[0].get('ids', {}).get('simkl_id')
        
        if not simkl_id:
            msg.reply_text(f"Found something, but couldn't retrieve its Simkl ID.")
            return

        # Step 2: Fetch the full extended details using the ID
        details_url = f"https://api.simkl.com/{media_type}/{simkl_id}?client_id={SIMKL_CLIENT_ID}&extended=full"
        details_req = urllib.request.Request(details_url, headers={'User-Agent': 'TheRealPhoenixBot/1.0'})
        
        with urllib.request.urlopen(details_req, context=context, timeout=8) as response:
            details = json.loads(response.read().decode('utf-8'))

        # Extract all the rich details
        title = details.get('title', 'Unknown Title')
        year = details.get('year', 'Unknown Year')
        status = details.get('status', 'Unknown Status')
        poster_id = details.get('poster')
        overview = details.get('overview', 'No synopsis available.')
        
        # Truncate the overview if it's super long so it doesn't flood the chat
        if len(overview) > 400:
            overview = overview[:397] + "..."
            
        # Construct the fancy caption
        link = f"https://simkl.com/{media_type}/{simkl_id}/"
        caption = f"🎬 *{title}* ({year})\n"
        caption += f"📌 *Status:* {status}\n\n"
        caption += f"📖 *Synopsis:* {overview}\n\n"
        caption += f"[View on Simkl]({link})"
        
        msg_id = msg.reply_to_message.message_id if msg.reply_to_message else msg.message_id

        # Send the poster if it exists, formatting it as a JPG for Telegram
        if poster_id:
            poster_url = f"https://simkl.in/posters/{poster_id}_m.jpg"
            bot.send_photo(
                chat_id=msg.chat_id, 
                photo=poster_url, 
                caption=caption, 
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=msg_id
            )
        else:
            msg.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=msg_id)
            
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
