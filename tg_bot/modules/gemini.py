# Modular Gemini AI Chatbot Module for TheRealPhoenixBot
# Built using the modern, non-deprecated google-genai SDK

import os
import logging
from google import genai
from google.genai import types
from telegram import Bot, Update, ParseMode
from telegram.ext import MessageHandler, Filters, run_async
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler

LOGGER = logging.getLogger(__name__)

# Initialize client using the modern SDK structure
API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if API_KEY:
    # Under google-genai, we initialize a client instance
    client = genai.Client(api_key=API_KEY)
    # Using the standard flash model identifier
    MODEL_NAME = 'gemini-1.5-flash'
else:
    LOGGER.warning("AI_API_KEY / GEMINI_API_KEY is not set. Gemini module will be disabled.")
    client = None


def generate_ai_response(prompt: str) -> str:
    """Helper function to call Gemini API using the modern SDK structure."""
    if not client:
        return "I'm sorry, but my AI core is currently offline (API key missing)."
    
    try:
        # Define modern system instructions
        config = types.GenerateContentConfig(
            system_instruction=(
                "You are Phoenix, a helpful, authentic, and witty AI companion bot in a Telegram chat. "
                "Respond concisely, keep formatting clean (use basic markdown safely), and match the conversational tone of the user."
            )
        )
        # Call API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        return response.text.strip()
    except Exception as e:
        LOGGER.error(f"[gemini] Gemini API execution failed: {e}")
        return "Sorry, I had a brief neural misfire. Could you try asking that again?"


@run_async
def ask_ai(bot: Bot, update: Update, args):
    """Handles explicit command inquiries, e.g., /ask tell me a joke"""
    msg = update.effective_message
    query = " ".join(args)

    if not query:
        msg.reply_text("Please provide a question! Example: `/ask why is the sky blue?`", parse_mode=ParseMode.MARKDOWN)
        return

    # Send typing action so users know the bot is "thinking"
    bot.send_chat_action(chat_id=msg.chat_id, action="typing")
    
    response = generate_ai_response(query)
    msg.reply_text(response)


@run_async
def mention_chatbot(bot: Bot, update: Update):
    """Handles auto-replying when the bot is tagged (@TheRealPhoenixBot) in groups or PM'd directly."""
    msg = update.effective_message
    
    # Extract the query text, removing the bot's tag if present
    query = msg.text
    bot_username = f"@{bot.username}"
    
    if bot_username in query:
        query = query.replace(bot_username, "").strip()
    
    if not query:
        return # Avoid responding to empty tags

    bot.send_chat_action(chat_id=msg.chat_id, action="typing")
    response = generate_ai_response(query)
    msg.reply_text(response)


# 1. Command handler: triggers on `/ask [question]` or `/ai [question]`
ASK_HANDLER = DisableAbleCommandHandler(["ask", "ai"], ask_ai, pass_args=True)
dispatcher.add_handler(ASK_HANDLER)

# 2. Mention handler: triggers when the bot's username is tagged, or when direct messaged in PM
MENTION_HANDLER = MessageHandler(
    Filters.text & (Filters.entity("mention") | Filters.private), 
    mention_chatbot
)
dispatcher.add_handler(MENTION_HANDLER)

# Module details for the main system
__help__ = """
Let's make the bot conversational! You can interact with the built-in Gemini AI model.

*Available commands:*
 - /ask <question>: Ask the AI any question directly.
 - /ai <question>: Same as /ask.
 
*Alternative:*
- Simply tag the bot (`@bot_username`) in a group message, or message it in private, and it will automatically answer you using AI!
"""

__mod_name__ = "Gemini"
