from core.bot_sys import (
    admin_cao,
    get_welcome_caption,
    set_welcome_caption,
    reset_welcome_caption,
    get_bye_caption,
    set_bye_caption,
    reset_bye_caption,
)
from zlapi.models import Message, ThreadType, MessageStyle, MultiMsgStyle

RAINBOW_COLORS = ["#f00e0e", "#f8f700", "#09f926", "#233ee6", "#46d0e5", "#9b23e6", "#f91be4", "#fe1e1e", "#da2df2", "#fbfbfb"]
NEON_COLORS = ["#00e5ff", "#ff4081", "#ffeb3b", "#00e676", "#ff9100", "#e040fb", "#18ffff", "#ff1744"]


def _styled_msg(text, colors=None, font_size="14"):
    """Create a Message with rainbow colored text lines."""
    if colors is None:
        colors = RAINBOW_COLORS
    lines = text.split('\n')
    styles = []
    offset = 0
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        styles.append(MessageStyle(style="color", color=color, offset=offset, length=len(line), auto_format=False))
        offset += len(line) + 1
    if lines:
        styles.append(MessageStyle(style="font", size=font_size, offset=0, length=offset - 1, auto_format=False))
    return Message(text=text, style=MultiMsgStyle(styles))


def _get_reply_text(client, message_object, thread_id):
    """Try to get text from replied message."""
    try:
        quote = getattr(message_object, 'quote', None)
        if not quote:
            return None
        # Try direct content from quote first
        q_content = getattr(quote, 'content', None) or getattr(quote, 'qmsg', None)
        if q_content and isinstance(q_content, str) and q_content.strip():
            return q_content.strip()
        # Fallback: search message_history
        q_msg_id = getattr(quote, 'globalMsgId', None) or getattr(quote, 'msgId', None)
        if not q_msg_id:
            return None
        history = getattr(client, 'message_history', {}).get(thread_id, [])
        for m in reversed(history):
            if str(m.get('msgId', '')) == str(q_msg_id):
                return m.get('text', '')
    except Exception as e:
        print(f"[DEBUG] _get_reply_text error: {e}")
    return None


def _send_styled_reply(client, message_object, text, thread_id, thread_type, colors=None):
    client.replyMessage(_styled_msg(text, colors), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)


def handle_welcome_command(message_object, thread_id, thread_type, author_id, client):
    if not admin_cao(client, author_id):
        _send_styled_reply(client, message_object, "❌ Bạn không phải admin bot!", thread_id, thread_type)
        return

    content = getattr(message_object, 'content', '') or ''
    parts = content.split(None, 2)
    if len(parts) < 2:
        _send_styled_reply(
            client, message_object,
            "❌ Thiếu tham số!\n💡 Dùng: welcome set/show/default",
            thread_id, thread_type
        )
        return

    sub = parts[1].lower()

    if sub == "set":
        caption = None
        if len(parts) >= 3:
            caption = parts[2].strip()
        else:
            caption = _get_reply_text(client, message_object, thread_id)

        if not caption:
            _send_styled_reply(
                client, message_object,
                "❌ Thiếu caption!\n"
                "💡 Cách dùng:\n"
                "• Gõ: welcome set <nội dung>\n"
                "• Hoặc reply tin nhắn rồi gõ: welcome set",
                thread_id, thread_type
            )
            return

        set_welcome_caption(client, thread_id, caption)
        _send_styled_reply(
            client, message_object,
            "[ 🎉 CẬP NHẬT THÀNH CÔNG ]\n"
            "> Caption chào mừng đã được lưu!\n"
            "> Gõ welcome show để xem.",
            thread_id, thread_type
        )

    elif sub == "show":
        caption = get_welcome_caption(client, thread_id)
        text = (
            "[ 🎉 CẤU HÌNH CHÀO MỪNG ]\n"
            f"> Caption: {caption}\n"
            ">\n"
            "> 🔮 Biến hỗ trợ:\n"
            "> • {{user}}  → Tên thành viên\n"
            "> • {{group}} → Tên nhóm\n"
            "> • {{member}}→ Số thành viên\n"
            "> • {{type}}  → Loại (nhóm)\n"
            "> • {{admin}} → Người duyệt/kick"
        )
        _send_styled_reply(client, message_object, text, thread_id, thread_type)

    elif sub == "default":
        reset_welcome_caption(client, thread_id)
        _send_styled_reply(
            client, message_object,
            "[ 🔄 ĐẶT LẠI MẶC ĐỊNH ]\n"
            "> Caption chào mừng đã được\n"
            "> khôi phục về mặc định!",
            thread_id, thread_type
        )

    else:
        _send_styled_reply(
            client, message_object,
            "❌ Tham số không hợp lệ!\n💡 Dùng: welcome set/show/default",
            thread_id, thread_type
        )


def handle_bye_command(message_object, thread_id, thread_type, author_id, client):
    if not admin_cao(client, author_id):
        _send_styled_reply(client, message_object, "❌ Bạn không phải admin bot!", thread_id, thread_type)
        return

    content = getattr(message_object, 'content', '') or ''
    parts = content.split(None, 2)
    if len(parts) < 2:
        _send_styled_reply(
            client, message_object,
            "❌ Thiếu tham số!\n💡 Dùng: bye set/show/default",
            thread_id, thread_type
        )
        return

    sub = parts[1].lower()

    if sub == "set":
        caption = None
        if len(parts) >= 3:
            caption = parts[2].strip()
        else:
            caption = _get_reply_text(client, message_object, thread_id)

        if not caption:
            _send_styled_reply(
                client, message_object,
                "❌ Thiếu caption!\n"
                "💡 Cách dùng:\n"
                "• Gõ: bye set <nội dung>\n"
                "• Hoặc reply tin nhắn rồi gõ: bye set",
                thread_id, thread_type
            )
            return

        set_bye_caption(client, thread_id, caption)
        _send_styled_reply(
            client, message_object,
            "[ 👋 CẬP NHẬT THÀNH CÔNG ]\n"
            "> Caption tạm biệt đã được lưu!\n"
            "> Gõ bye show để xem.",
            thread_id, thread_type
        )

    elif sub == "show":
        caption = get_bye_caption(client, thread_id)
        text = (
            "[ 👋 CẤU HÌNH TẠM BIỆT ]\n"
            f"> Caption: {caption}\n"
            ">\n"
            "> 🔮 Biến hỗ trợ:\n"
            "> • {{user}}  → Tên thành viên\n"
            "> • {{group}} → Tên nhóm\n"
            "> • {{member}}→ Số thành viên\n"
            "> • {{type}}  → Loại (nhóm)\n"
            "> • {{admin}} → Người duyệt/kick"
        )
        _send_styled_reply(client, message_object, text, thread_id, thread_type)

    elif sub == "default":
        reset_bye_caption(client, thread_id)
        _send_styled_reply(
            client, message_object,
            "[ 🔄 ĐẶT LẠI MẶC ĐỊNH ]\n"
            "> Caption tạm biệt đã được\n"
            "> khôi phục về mặc định!",
            thread_id, thread_type
        )

    else:
        _send_styled_reply(
            client, message_object,
            "❌ Tham số không hợp lệ!\n💡 Dùng: bye set/show/default",
            thread_id, thread_type
        )


txa = {
    "name": "pro_welcome",
    "desc": {
        "welcome": "Quản lý caption chào mừng (admin bot)",
        "bye": "Quản lý caption tạm biệt (admin bot)"
    },
    "author": "TXA",
    "command": ['welcome', 'bye']
}


def txa_command(bot, message_object, thread_id, thread_type, author_id, message_text):
    prefix = getattr(bot, 'prefix', '.')
    cmd = message_text[len(prefix):].split()[0].lower()

    dispatch_map = {
        'welcome': handle_welcome_command,
        'bye': handle_bye_command,
    }

    func = dispatch_map.get(cmd)
    if func:
        import inspect
        sig = inspect.signature(func)
        args_map = {
            'bot': bot,
            'client': bot,
            'message_object': message_object,
            'thread_id': thread_id,
            'thread_type': thread_type,
            'author_id': author_id,
            'message': message_text,
            'message_text': message_text,
            'message_lower': message_text.lower()
        }
        args = []
        for param_name in sig.parameters:
            if param_name in args_map:
                args.append(args_map[param_name])
            else:
                args.append(None)
        func(*args)
