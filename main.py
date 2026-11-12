import time
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# التوكن وكلمة السر
BOT_TOKEN = '9102308309:AAGQFjQTBMcRkxB8qt78FfjyLPLHw5qOnQc'
ADMIN_PASSWORD = '123123opop'

bot = telebot.TeleBot(BOT_TOKEN)

# المتغيرات لحفظ البيانات
forbidden_words = set()      # قائمة الكلمات المحظورة
authenticated_users = set()  # قائمة الأدمنية المسجلين
user_states = {}             # تتبع حالة المستخدم

# الوقت الافتراضي للحذف (ساعتين = 7200 ثانية)
deletion_time_seconds = 7200 

# عدّاد إحصائيات المخالفات المحذوفة
total_deleted_count = 0


def delete_message_after_delay(chat_id, message_id, delay_seconds):
    """دالة لحذف الرسالة بعد انقضاء الوقت المحدد وزيادة العدّاد"""
    global total_deleted_count
    time.sleep(delay_seconds)
    try:
        bot.delete_message(chat_id, message_id)
        total_deleted_count += 1
        print(f"[تم الحذف] حُذفت رسالة مخالفة. الإجمالي: {total_deleted_count}")
    except Exception as e:
        print(f"[خطأ في الحذف] لم نتمكن من حذف الرسالة: {e}")


def main_menu_keyboard():
    """أزرار واجهة التحكم"""
    current_mins = int(deletion_time_seconds / 60)
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("➕ إضافة كلمات", callback_data="add_word"),
        InlineKeyboardButton("❌ حذف كلمة", callback_data="remove_word")
    )
    markup.row(
        InlineKeyboardButton("📋 عرض الكلمات المحظورة", callback_data="list_words")
    )
    markup.row(
        InlineKeyboardButton(f"📊 إحصائيات الحذف: {total_deleted_count}", callback_data="show_stats")
    )
    markup.row(
        InlineKeyboardButton(f"⏱ وقت الحذف الحالي: {current_mins} دقيقة", callback_data="show_time")
    )
    return markup


# ------------------ الأوامر وتسجيل الدخول ------------------

@bot.message_handler(commands=['start', 'admin', 'count'])
def send_welcome(message):
    user_id = message.from_user.id
    text = message.text

    if user_id not in authenticated_users:
        if text and text.startswith('/count'):
            bot.reply_to(message, "❌ يجب عليك تسجيل الدخول أولاً عبر إرسال كلمة السر.")
            return
        user_states[user_id] = 'awaiting_password'
        bot.reply_to(message, "🔒 هذا البوت محمي. الرجاء إدخال كلمة السر:")
        return

    # إذا كان الأمر هو /count وأنت مسجل دخول
    if text and text.startswith('/count'):
        bot.reply_to(message, f"📊 عدد الكلمات المحظورة حالياً: {len(forbidden_words)} كلمة.")
        return

    bot.reply_to(
        message,
        "أهلاً بك مجدداً في لوحة التحكم:",
        reply_markup=main_menu_keyboard()
    )


# ------------------ تغيير وقت الحذف أو إيقاف الإضافة ------------------

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/bot'))
def change_settings_by_command(message):
    user_id = message.from_user.id

    if user_id not in authenticated_users:
        bot.reply_to(message, "❌ يجب عليك تسجيل الدخول أولاً.")
        return

    command_text = message.text.strip()

    if command_text == '/botstop':
        user_states[user_id] = 'normal'
        bot.reply_to(
            message, 
            f"🛑 تم إيقاف وضع إضافة الكلمات.\nإجمالي الكلمات المحظورة: {len(forbidden_words)}",
            reply_markup=main_menu_keyboard()
        )
        return

    try:
        minutes_str = command_text.replace('/bot', '')
        minutes = int(minutes_str)

        if minutes <= 0:
            bot.reply_to(message, "❌ يجب أن يكون الوقت أكبر من صفر.")
            return

        global deletion_time_seconds
        deletion_time_seconds = minutes * 60

        bot.reply_to(
            message, 
            f"✅ تم تحديث وقت الحذف إلى **{minutes} دقيقة**.",
            reply_markup=main_menu_keyboard()
        )

    except ValueError:
        bot.reply_to(message, "❌ صيغة غير صحيحة. مثال: `/bot30` أو أرسل `/botstop` للخروج.")


# ------------------ التعامل مع الأزرار ------------------

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id

    if user_id not in authenticated_users:
        bot.answer_callback_query(call.id, "❌ غير مصرح لك!", show_alert=True)
        return

    if call.data == "add_word":
        user_states[user_id] = 'awaiting_words_batch'
        bot.send_message(
            call.message.chat.id, 
            "✏️ **وضع إضافة الكلمات مفعّل:**\nأرسل الكلمات الآن **كلمة تلو الأخرى**.\nوعندما تنتهي، أرسل الأمر:\n`/botstop`",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    elif call.data == "remove_word":
        if not forbidden_words:
            bot.answer_callback_query(call.id, "القائمة فارغة!", show_alert=True)
            return
        user_states[user_id] = 'awaiting_word_to_remove'
        words_str = "\n".join([f"• {w}" for w in forbidden_words])
        bot.send_message(call.message.chat.id, f"🗑️ الكلمات الحالية:\n{words_str}\n\nأرسل الكلمة التي تريد حذفها:")
        bot.answer_callback_query(call.id)

    elif call.data == "list_words":
        if not forbidden_words:
            msg = "📋 لا توجد أي كلمات محظورة حالياً."
        else:
            words_str = "\n".join([f"• {w}" for w in forbidden_words])
            msg = f"📋 قائمة الكلمات المحظورة ({len(forbidden_words)} كلمة):\n\n{words_str}"
        
        bot.send_message(call.message.chat.id, msg, reply_markup=main_menu_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "show_stats":
        bot.answer_callback_query(
            call.id, 
            f"📊 إجمالي الرسائل التي تم حذفها: {total_deleted_count}", 
            show_alert=True
        )

    elif call.data == "show_time":
        current_mins = int(deletion_time_seconds / 60)
        bot.answer_callback_query(
            call.id, 
            f"وقت الحذف الحالي هو بعد {current_mins} دقيقة.", 
            show_alert=True
        )


# ------------------ معالج الرسائل النصية ------------------

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if not text:
        return

    # إذا أرسل /botstop بالخطأ كرسالة عادية
    if text.strip() == '/botstop':
        if user_id in authenticated_users:
            user_states[user_id] = 'normal'
            bot.reply_to(message, f"🛑 تم إيقاف إضافة الكلمات. الإجمالي: {len(forbidden_words)}", reply_markup=main_menu_keyboard())
            return

    if user_id in user_states:
        state = user_states[user_id]

        if state == 'awaiting_password':
            if text == ADMIN_PASSWORD:
                authenticated_users.add(user_id)
                user_states[user_id] = 'normal'
                bot.reply_to(message, "✅ كلمة السر صحيحة! تم تسجيل دخولك.", reply_markup=main_menu_keyboard())
            else:
                bot.reply_to(message, "❌ كلمة السر خاطئة! حاول مجدداً:")
            return

        elif state == 'awaiting_words_batch':
            word_to_add = text.strip().lower()
            forbidden_words.add(word_to_add)
            bot.reply_to(message, f"➕ تمت إضافة: ({word_to_add})\nأرسل كلمة أخرى أو أرسل `/botstop` للإنهاء.")
            return

        elif state == 'awaiting_word_to_remove':
            word_to_remove = text.strip().lower()
            if word_to_remove in forbidden_words:
                forbidden_words.remove(word_to_remove)
                bot.reply_to(message, f"🗑️ تم حذف الكلمة: ({word_to_remove})", reply_markup=main_menu_keyboard())
            else:
                bot.reply_to(message, "❌ الكلمة غير موجودة.", reply_markup=main_menu_keyboard())
            user_states[user_id] = 'normal'
            return

    # فحص الكلمات المحظورة فقط
    text_lower = text.lower()
    for word in forbidden_words:
        if word in text_lower:
            current_delay = deletion_time_seconds
            print(f"[رصد مخالفة] تم رصد الكلمة '{word}'. سيتم الحذف خلال {current_delay / 60} دقيقة.")
            
            threading.Thread(
                target=delete_message_after_delay,
                args=(message.chat.id, message.message_id, current_delay)
            ).start()
            break


print("البوت يعمل الآن وجاهز بكل التعديلات...")
bot.infinity_polling()
