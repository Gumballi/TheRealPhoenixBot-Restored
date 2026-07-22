# Modular AI Chatbot module for TheRealPhoenixBot
# Automatically retries transient errors (503/429/overload) and fails over from
# Gemini to Mistral so a single provider's outage doesn't take /ask down entirely.
# Upgraded with YouTube Transcript extraction capabilities.

import os
import time
import logging
import re

from telegram import Bot, Update, ParseMode
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Phoenix, a helpful, authentic, and witty AI companion bot in a Telegram chat. "
    "Respond concisely, keep formatting clean (use basic markdown safely), and match the conversational tone of the user."
)

# ---------------------------------------------------------------------------
# Gemini setup
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash"  # avoid pinning to a dated model - these get retired
gemini_client = None
genai_types = None

if GEMINI_API_KEY:
    try:
        from google import genai
        from google.genai import types as genai_types
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        LOGGER.error(f"[ai] Failed to initialize Gemini client: {e}")
else:
    LOGGER.warning("[ai] AI_API_KEY / GEMINI_API_KEY not set - Gemini provider disabled.")

# ---------------------------------------------------------------------------
# Mistral setup
# ---------------------------------------------------------------------------
try:
    from tg_bot import MISTRAL_API_KEY
except ImportError:
    MISTRAL_API_KEY = None

if not MISTRAL_API_KEY:
    MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

MISTRAL_MODEL = "mistral-large-latest"
mistral_client = None

if MISTRAL_API_KEY:
    try:
        # Use a shim to handle both mistralai v1 and v2 SDKs cleanly
        try:
            from mistralai.client import Mistral
        except ImportError:
            from mistralai import Mistral

        mistral_client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as e:
        LOGGER.error(f"[ai] Failed to initialize Mistral client: {e}")
else:
    LOGGER.warning("[ai] MISTRAL_API_KEY not set - Mistral fallback disabled.")

# Order providers are tried in. Override via env if you want Mistral tried first
PROVIDER_ORDER = [
    p.strip().lower()
    for p in os.environ.get("AI_PROVIDER_ORDER", "gemini,mistral").split(",")
    if p.strip()
]

MAX_RETRIES_PER_PROVIDER = 2
BACKOFF_BASE_SECONDS = 1.5
TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "rate limit", "overloaded", "high demand", "timeout")

# ---------------------------------------------------------------------------
# Core AI Functions
# ---------------------------------------------------------------------------

def _is_transient(err: Exception) -> bool:
    text = str(err).lower()
    return any(marker.lower() in text for marker in TRANSIENT_MARKERS)

def _call_gemini(prompt: str) -> str:
    config = genai_types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return response.text.strip()

def _call_mistral(prompt: str) -> str:
    response = mistral_client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()

PROVIDERS = {
    "gemini": (lambda: gemini_client is not None, _call_gemini),
    "mistral": (lambda: mistral_client is not None, _call_mistral),
}

def generate_ai_response(prompt: str) -> str:
    last_error = None
    tried_any = False

    for provider_name in PROVIDER_ORDER:
        provider = PROVIDERS.get(provider_name)
        if not provider:
            LOGGER.warning(f"[ai] Unknown provider '{provider_name}' in AI_PROVIDER_ORDER, skipping.")
            continue

        is_available, call_fn = provider
        if not is_available():
            continue

        tried_any = True
        for attempt in range(1, MAX_RETRIES_PER_PROVIDER + 1):
            try:
                return call_fn(prompt)
            except Exception as e:
                last_error = e
                transient = _is_transient(e)
                LOGGER.warning(
                    f"[ai] {provider_name} attempt {attempt}/{MAX_RETRIES_PER_PROVIDER} failed "
                    f"({'transient, will retry' if transient else 'non-transient, giving up on this provider'}): {e}"
                )
                if not transient:
                    break
                if attempt < MAX_RETRIES_PER_PROVIDER:
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

        LOGGER.error(f"[ai] {provider_name} exhausted retries, moving to next provider if any.")

    if not tried_any:
        LOGGER.error("[ai] No AI providers are configured (missing API keys).")
        return "I'm sorry, but my AI core is currently offline (no API keys configured)."

    LOGGER.error(f"[ai] All configured providers failed. Last error: {last_error}")
    return "Sorry, I had a brief neural misfire. Could you try asking that again?"

# ---------------------------------------------------------------------------
# YouTube Transcript Integration
# ---------------------------------------------------------------------------

def _get_youtube_transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Stitch all subtitle blocks together
        text = " ".join([t['text'] for t in transcript_list])
        # Truncate at ~15,000 characters to prevent overloading token limits on massive videos
        if len(text) > 15000:
            text = text[:15000] + "... [Transcript truncated due to length]"
        return text
    except ImportError:
        LOGGER.error("[ai] youtube-transcript-api is not installed!")
        return None
    except Exception as e:
        LOGGER.warning(f"[ai] Could not fetch transcript for {video_id}: {e}")
        return None

def enhance_prompt_with_youtube(prompt: str) -> str:
    """Scans the prompt for a YouTube link, fetches the transcript, and silently injects it for the AI."""
    yt_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(yt_pattern, prompt)
    
    if match:
        video_id = match.group(1)
        transcript = _get_youtube_transcript(video_id)
        
        if transcript:
            return prompt + f"\n\n[System Note: A YouTube video was linked. Here is the hidden video transcript for you to analyze and answer the user's question:\n{transcript}]"
        else:
            return prompt + f"\n\n[System Note: A YouTube video was linked, but closed captions are disabled or unavailable. Inform the user you cannot 'watch' it without a transcript.]"
            
    return prompt

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@run_async
def ask_ai(bot: Bot, update: Update, args):
    msg = update.effective_message
    query = " ".join(args)

    if not query:
        msg.reply_text("Please provide a question! Example: `/ask why is the sky blue?`", parse_mode=ParseMode.MARKDOWN)
        return

    prompt = query
    if msg.reply_to_message:
        context_text = msg.reply_to_message.caption or msg.reply_to_message.text
        if context_text:
            prompt = f"Previous message context:\n{context_text.strip()}\n\nUser question: {query}"

    prompt = enhance_prompt_with_youtube(prompt)

    bot.send_chat_action(chat_id=msg.chat_id, action="typing")
    response = generate_ai_response(prompt)
    msg.reply_text(response)

@run_async
def mention_chatbot(bot: Bot, update: Update):
    msg = update.effective_message
    if not msg or not msg.text:
        return

    is_pm = update.effective_chat.type == "private"
    bot_username = f"@{bot.username}" if bot.username else ""

    is_mentioned = bool(
        bot_username and bot_username.lower() in msg.text.lower()
    )

    is_reply_to_bot = bool(
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == bot.id
    )

    if not (is_pm or is_mentioned or is_reply_to_bot):
        return

    LOGGER.info(
        f"[ai] mention_chatbot triggered by {msg.from_user.id} in chat {msg.chat_id} "
        f"(PM: {is_pm}, Mention: {is_mentioned}, ReplyToBot: {is_reply_to_bot})"
    )

    query = msg.text
    if bot_username and bot_username.lower() in query.lower():
        query = re.sub(re.escape(bot_username), "", query, flags=re.IGNORECASE).strip()

    if not query:
        return

    if is_reply_to_bot and msg.reply_to_message:
        previous_text = msg.reply_to_message.caption or msg.reply_to_message.text
        if previous_text:
            prompt = f"Previous message context:\n{previous_text.strip()}\n\nUser reply: {query}"
        else:
            prompt = query
    else:
        prompt = query

    prompt = enhance_prompt_with_youtube(prompt)

    bot.send_chat_action(chat_id=msg.chat_id, action="typing")
    response = generate_ai_response(prompt)
    msg.reply_text(response)

@run_async
def ai_status(bot: Bot, update: Update):
    lines = ["*AI provider status:*"]
    for name in PROVIDER_ORDER:
        provider = PROVIDERS.get(name)
        if not provider:
            lines.append(f"- `{name}`: unknown provider name")
            continue
        is_available, _ = provider
        status = "configured" if is_available() else "NOT configured (missing API key)"
        lines.append(f"- `{name}`: {status}")
    update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


ASK_HANDLER = DisableAbleCommandHandler(["ask", "ai"], ask_ai, pass_args=True)
dispatcher.add_handler(ASK_HANDLER)

MENTION_HANDLER = MessageHandler(
    Filters.text & (Filters.entity("mention") | Filters.entity("text_mention") | Filters.private | Filters.reply) & (~Filters.command),
    mention_chatbot,
)
dispatcher.add_handler(MENTION_HANDLER, group=10)

AI_STATUS_HANDLER = CommandHandler("aistatus", ai_status)
dispatcher.add_handler(AI_STATUS_HANDLER)

__help__ = """
Let's make the bot conversational! You can interact with the built-in AI model.

*Available commands:*
 - /ask <question>: Ask the AI any question directly.
 - /ai <question>: Same as /ask.
 - /aistatus: Shows which AI providers are configured and their fallback order.

*Alternative:*
- Simply tag the bot (`@bot_username`) in a group message, or message it in private, and it will automatically answer you using AI!

*YouTube Support:*
If you send a YouTube link to the AI, it will attempt to extract the closed captions and answer questions about the video!

*Reliability:*
This module automatically retries and fails over between providers (currently Gemini and Mistral, in that order) if one is temporarily overloaded.
"""

__mod_name__ = "AI Chatbot"
