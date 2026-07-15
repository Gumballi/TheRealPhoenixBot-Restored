# Simple lyrics module using public tokenless APIs by @TheRealPhoenix

import io
import json
import logging
import urllib.request
import urllib.parse
from telegram import Bot, Update
from telegram.ext import run_async
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

LOGGER = logging.getLogger(__name__)


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
                headers={
                    # LRCLIB is known to silently drop connections for some
                    # bot-like User-Agent strings. A browser-style UA with a
                    # real project link (per LRCLIB's own recommended format)
                    # is far less likely to be filtered.
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; PhoenixLyricsBot/1.0; "
                        "+https://github.com/Gumballi/TheRealPhoenixBot-Restored)"
                    )
                },
            )

            # LRCLIB can be slow on a cache miss since it may reach out to
            # external sources before responding, so give it more headroom
            # than a typical API call.
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data:
                    track = data[0]
                    lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
                    if lyrics:
                        meta = (
                            f"✨ {track.get('trackName', '')} — "
                            f"{track.get('artistName', '')} ✨\n\n"
                        )
                        return meta + lyrics.strip()
        except Exception as e:
            # Log the real error instead of silently swallowing it -
            # otherwise every failure (network, timeout, blocked UA,
            # malformed JSON, etc.) just looks like "song not found".
            LOGGER.warning(f"[lyrics] fetch failed for query '{query}': {e!r}")
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

    # Check against the absolute Telegram maximum text limit (4096 characters)
    if len(lyrics_text) > 4090:
        # Create an in-memory text file instead of writing to disk.
        # This prevents disk usage errors and parallel processing write collisions.
        lyric_file = io.BytesIO(bytes(f"{lyrics_text}\n\n\nOwO UwU OmO", "utf-8"))
        lyric_file.name = f"{query.replace(' ', '_')}_lyrics.txt"
        
        msg.reply_document(
            document=lyric_file,
            caption="Message length exceeded the maximum limit! Sending as a text file.",
        )
    else:
        # Send text as plain text to avoid unclosed Markdown errors from lyric symbols
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
