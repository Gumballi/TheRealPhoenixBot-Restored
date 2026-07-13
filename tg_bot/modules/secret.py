import uuid
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.users import get_user_id

# Internal storage for active anonymous secrets
ANON_SECRET_DB = {}

@run_async
def anonymous_secret_trigger(update: Update, context: CallbackContext):
    message = update.effective_message
    if not message or not message.text:
        return

    # Pattern: @BotUsername @TargetUsername Secret Message
    bot_username = context.bot.username
    pattern = rf"^@{re.escape(bot_username)}\s+(@\w+)\s+(.+)"
    match = re.match(pattern, message.text, re.IGNORECASE | re.DOTALL)
    
    if not match:
        return

    target_username = match.group(1)
    secret_text = match.group(2)
    sender_user = message.from_user

    # Extract user ID from username using the repo's internal function
    target_user_id = get_user_id(target_username)

    if not target_user_id:
        message.reply_text(f"Could not find user '{target_username}'. Please ensure the bot has interacted with them before.")
        return

    if target_user_id == sender_user.id:
        message.reply_text("You can't send an anonymous secret message to yourself!")
        return

    # Generate a unique key for this secret instance
    secret_id = str(uuid.uuid4())[:8]

    # Store the payload details
    ANON_SECRET_DB[secret_id] = {
        "text": secret_text,
        "target_id": target_user_id,
        "sender_id": sender_user.id
    }

    # Build the interaction layout button
    keyboard = [[InlineKeyboardButton(text="Reveal Anonymous Secret", callback_data=f"anonsecret_{secret_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Inform the chat an anonymous secret message is waiting
    text = (
        f"*An Anonymous Secret Message Has Arrived!*\n\n"
        f"*For:* {target_username}\n\n"
        f"_Only the designated recipient can open this text frame._"
    )
    
    message.chat.send_message(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Delete the triggering command so the raw text vanishes from the chat log
    try:
        message.delete()
    except Exception:
        pass


@run_async
def read_anonymous_secret(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    secret_id = query.data.split("_")[1]

    if secret_id not in ANON_SECRET_DB:
        query.answer(text="Error: This anonymous secret message has expired or no longer exists.", show_alert=True)
        return

    secret_data = ANON_SECRET_DB[secret_id]

    if user_id != secret_data["target_id"]:
        query.answer(text="Access Denied! This anonymous secret envelope belongs to someone else.", show_alert=True)
        return

    query.answer(text=f"Decrypted Anonymous Message:\n\n{secret_data['text']}", show_alert=True)


# Register handlers
dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups, anonymous_secret_trigger))
dispatcher.add_handler(CallbackQueryHandler(read_anonymous_secret, pattern=r"^anonsecret_"))

__mod_name__ = "Anonymous Secrets"
__help__ = """
Send anonymous secret messages to users in a group using a mention trigger.

Usage:
`@{bot_username} @username <your hidden text>`: Send an anonymous secret message to a user by username.
""".format(bot_username=dispatcher.bot.username)

