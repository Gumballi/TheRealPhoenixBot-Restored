import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from tg_bot import dispatcher

# Internal storage for active secrets
SECRET_DB = {}

def send_secret(update: Update, context: CallbackContext):
    message = update.effective_message
    chat = update.effective_chat
    
    # Prerequisite: Must be a reply to a target user
    if not message.reply_to_message:
        message.reply_text("❌ Please reply to the user you want to send a secret message to.")
        return

    # Extract the secret message text (everything after /secret)
    args = context.args
    if not args:
        message.reply_text("⚠️ Usage: Reply to a user with `/secret <your hidden text>`")
        return
        
    secret_text = " ".join(args)
    target_user = message.reply_to_message.from_user
    sender_user = message.from_user

    if target_user.id == sender_user.id:
        message.reply_text("🔒 You can't send a secret message to yourself!")
        return

    # Generate a unique key for this secret instance
    secret_id = str(uuid.uuid4())[:8]

    # Store the payload details mapping out IDs
    SECRET_DB[secret_id] = {
        "text": secret_text,
        "target_id": target_user.id,
        "sender_id": sender_user.id
    }

    # Build the interaction layout button
    keyboard = [
        [
            InlineKeyboardButton(
                text="👁️ Reveal Secret", 
                callback_data=f"secret_{secret_id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Inform the chat a secret message is waiting
    text = (
        f"🔒 *A Secret Message Has Arrived!*\n\n"
        f"👤 *From:* {sender_user.first_name}\n"
        f"🎯 *For:* {target_user.first_name}\n\n"
        f"_Only the designated recipient can open this text frame._"
    )
    
    chat.send_message(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    
    # Delete the triggering command so the raw text vanishes from the chat log
    try:
        message.delete()
    except Exception:
        # Fails silently if the bot isn't granted group admin deletion rights
        pass


def read_secret(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Extract the unique ID from callback_data
    secret_id = query.data.split("_")[1]

    if secret_id not in SECRET_DB:
        query.answer(text="⚠️ Error: This secret message has expired or no longer exists.", show_alert=True)
        return

    secret_data = SECRET_DB[secret_id]

    # Strict ID check validation (so missing usernames won't break anything)
    if user_id != secret_data["target_id"]:
        query.answer(text="🚫 Access Denied! This secret envelope belongs to someone else.", show_alert=True)
        return

    # Deliver the secret safely via an inline alert box pop-up
    query.answer(text=f"🔑 Decrypted Message:\n\n{secret_data['text']}", show_alert=True)


# Wire the actions into your bot's dispatcher instance using pure v13 syntax
dispatcher.add_handler(CommandHandler("secret", send_secret, run_async=True))
dispatcher.add_handler(CallbackQueryHandler(read_secret, pattern=r"^secret_", run_async=True))
