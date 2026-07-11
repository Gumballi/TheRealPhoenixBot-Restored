import uuid
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CallbackContext, CallbackQueryHandler, InlineQueryHandler

from tg_bot import dispatcher

# Internal storage for live secrets
SECRET_DB = {}

def inline_secret_handler(update: Update, context: CallbackContext):
    query_obj = update.inline_query
    query_text = query_obj.query.strip()

    if not query_text:
        return

    # Regex looks for: text context up until an '@' symbol at the end
    # Match pattern example: "My dark secret @target_username"
    match = re.search(r'(.*?)\s+@([A-Za-z0-9_]{5,32})$', query_text)
    
    if not match:
        # Show a helpful helper hint to the user while they are actively typing out their query
        results = [
            InlineQueryResultArticle(
                id="hint",
                title="Format Guide",
                description="Type: <secret text> @username",
                input_message_content=InputTextMessageContent(
                    "Standard Usage: Type `@botname your text @target` directly inside the input line."
                )
            )
        ]
        query_obj.answer(results, cache_time=1)
        return

    secret_payload = match.group(1).strip()
    target_username = match.group(2).strip().lower()
    sender = query_obj.from_user

    # Generate reference tracking identity keys
    secret_id = str(uuid.uuid4())[:8]
    SECRET_DB[secret_id] = {
        "text": secret_payload,
        "target_username": target_username,
        "sender_id": sender.id,
        "sender_name": sender.first_name
    }

    # Prepare user interface buttons
    keyboard = [
        [
            InlineKeyboardButton(
                text="👁️ Reveal Secret", 
                callback_data=f"secret_{secret_id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Frame output representation layout
    display_text = (
        f"*A Secret Message Has Arrived!*\n\n"
        f"**From:** {sender.mention_markdown_v2()}\n"
        f"**For:** @{target_username.replace('_', '\\_')}\n\n"
        f"_Only the matching target username can decrypt this capsule._"
    )

    results = [
        InlineQueryResultArticle(
            id=secret_id,
            title=f"Send Secret to @{target_username}",
            description=f"Message: {secret_payload[:30]}...",
            input_message_content=InputTextMessageContent(
                text=display_text, 
                parse_mode="MarkdownV2"
            ),
            reply_markup=reply_markup
        )
    ]

    query_obj.answer(results, cache_time=0, is_personal=True)


def read_inline_secret(update: Update, context: CallbackContext):
    query = update.callback_query
    current_user = query.from_user
    
    # Extract structural identifier token maps
    secret_id = query.data.split("_")[1]

    if secret_id not in SECRET_DB:
        query.answer(text="Error: This secret message has expired or no longer exists.", show_alert=True)
        return

    data = SECRET_DB[secret_id]
    
    current_username = (current_user.username or "").lower()

    # Double validation check (Matches both direct unique Telegram numeric ID OR raw textual target string handle matching)
    if current_username != data["target_username"]:
        query.answer(
            text=f"Access Denied! This secret envelope belongs exclusively to @{data['target_username']}.", 
            show_alert=True
        )
        return

    # Deliver target packet text cleanly via interactive alert notification container panels
    query.answer(text=f"Decrypted Message:\n\n{data['text']}", show_alert=True)


# Connect inline interaction mechanics to framework architecture distribution layers
dispatcher.add_handler(InlineQueryHandler(inline_secret_handler, run_async=True))
dispatcher.add_handler(CallbackQueryHandler(read_inline_secret, pattern=r"^secret_", run_async=True))
