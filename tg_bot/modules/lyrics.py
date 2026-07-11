import requests
import urllib.parse
from telegram import Bot, Update
from telegram.ext import run_async
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

class SongFetcher:
    @staticmethod
    def find_lyrics(query: str) -> str:
        """
        Queries the free public LRCLIB API to fetch plain lyrics without tokens.
        """
        try:
            url = f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}"
            # Emulate standard user agent to keep requests clean
            headers = {"User-Agent": "TelegramLyricsBot/1.0 (@TheRealPhoenix)"}
            response = requests.get(url, headers=headers, timeout=6)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Snag the top search result match
                    track = data[0]
                    lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
                    if lyrics:
                        # Prepend the title and artist metadata neatly to the text output
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

    # Call our internal tokenless fetcher instead of tswift
    lyrics_text = SongFetcher.find_lyrics(query)
    
    if not lyrics_text:
        msg.reply_text("Song lyrics not found!")
        return

    # Check Telegram message payload limitations
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
