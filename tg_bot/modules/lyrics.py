# Simple lyrics module using public tokenless APIs by @TheRealPhoenix

import json
import urllib.request
import urllib.parse
from telegram import Bot, Update
from telegram.ext import run_async
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

class SongFetcher:
    @staticmethod
    def find_lyrics(query: str) -> str:
        """
        Queries the free public LRCLIB API using Python's built-in urllib.
        No external dependencies required.
        """
        try:
            url = f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url, 
                headers={"User-Agent": "TelegramLyricsBot/1.0 (@TheRealPhoenix)"}
            )
            
            # Open the connection with a 6-second timeout
            with urllib.request.urlopen(req, timeout=6) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data:
                        track = data[0]
                        lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
                        if lyrics:
                            meta = f"✨ {track.get('trackName', '')} — {track.get('artistName', '')} ✨\n\n"
                            return meta + lyrics.strip()
        except Exception:
            pass
        return ""

@run_async
def lyrics(bot: Bot, update: Update, args):
    msg = update.effective_message
    query = " ".join(args)
    
    if not query:
        msg.reply_text("You haven't specified which song to look for!")
        return

    lyrics_text = SongFetcher.find_lyrics(query)
    
    if not lyrics_text:
        msg.reply_text("Song not found!")
        return

    if len(lyrics_text) > 4090:
        with open("lyrics.txt", 'w', encoding='utf-8') as f:
            f.write(f"{lyrics_text}\n\n\nOwO UwU OmO")
        with open("lyrics.txt", 'rb') as f:
            msg.reply_document(
                document=f,
                caption="Message length exceeded max limit! Sending as a text file."
            )
    else:
        msg.reply_text(lyrics_text)

__help__ = """
Want to get the lyrics of your favorite songs straight from the app? This module is perfect for that!

*Available commands:*
 - /lyrics <song>: returns the lyrics of that song.
 You can either enter just the song name or both the artist and song name.
"""

__mod_name__ = "Lyrics"

LYRICS_HANDLER = DisableAbleCommandHandler("lyrics", lyrics, pass_args=True)
dispatcher.add_handler(LYRICS_HANDLER)
