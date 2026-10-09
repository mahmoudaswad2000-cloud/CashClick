import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# التوكن الجديد الخاص بك
API_TOKEN = "8845579928:AAGOSVEYrB1q-xmVYvn5t2ADpcg8Frort9w"
MONETAG_LINK = "https://uplcm.com/4/11967886"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ==================== إعداد قاعدة البيانات (SQLite) ====================
conn = sqlite3.connect("cashclick_bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    ads_today INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    invited_by INTEGER,
    last_click_time REAL DEFAULT 0,
    click_streak INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0
)
""")
conn.commit()


def get_user(user_id):
  cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
  return cursor.fetchone()


def add_user(user_id, invited_by=None):
  if not get_user(user_id):
    cursor.execute(
        "INSERT INTO users (user_id, invited_by) VALUES (?, ?)",
        (user_id, invited_by),
    )
    conn.commit()


# ==================== القوائم التفاعلية ====================
def main_menu():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📺 مشاهدة الإعلانات المربحة", callback_data="watch_ads"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💰 رصيدي وإحصائياتي", callback_data="profile"
              )
          ],
          [
              InlineKeyboardButton(
                  text="👥 دعوة أصدقاء (الإحالات)", callback_data="referral"
              )
          ],
          [InlineKeyboardButton(text="💸 طلب سحب الأرباح", callback_data="withdraw")],
      ]
  )


def back_to_home():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]
      ]
  )


# ==================== الأوامر والأحداث ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  user_id = message.from_user.id

  args = message.text.split()
  invited_by = None
  if len(args) > 1 and args[1].startswith("ref_"):
    try:
      potential_inviter = int(args[1].replace("ref_", ""))
      if potential_inviter != user_id:
        invited_by = potential_inviter
    except ValueError:
      pass

  if not get_user(user_id):
    add_user(user_id, invited_by)
    if invited_by and get_user(invited_by):
      cursor.execute(
          "UPDATE users SET referrals = referrals + 1 WHERE user_id = ?",
          (invited_by,),
      )
      conn.commit()

  user = get_user(user_id)
  if user and user[7] == 1:
    await message.answer(
        "⛔ عذراً، تم حظرك نهائياً من البوت بسبب اكتشاف نشاط مشبوه."
    )
    return

  welcome_text = (
      f"🌟 **أهلاً بك في بوت CashClick | ربح الأقوياء!** 🌟\n\n"
      f"🎮 اجمع أرباحك يومياً عبر مشاهدة الإعلانات واسحبها بسهولة عند إتمام الشروط:\n\n"
      f"🎯 **شروط البوت:**\n"
      f"• الحد الأدنى للسحب: **200 دولار**.\n"
      f"• شرط فتح السحب: دعوة **25 إحالة** حقيقية.\n\n"
      f"اختر ما يناسبك من القائمة أدناه:"
  )
  await message.answer(welcome_text, reply_markup=main_menu())


@dp.callback_query(F.data == "main_menu")
async def main_menu_cb(callback: types.CallbackQuery):
  user = get_user(callback.from_user.id)
  if user and user[7] == 1:
    return await callback.answer("حسابك محظور!", show_alert=True)

  await callback.message.edit_text(
      "🏠 **القائمة الرئيسية لـ CashClick:**", reply_markup=main_menu()
  )
  await callback.answer()


@dp.callback_query(F.data == "watch_ads")
async def watch_ads_handler(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  user = get_user(user_id)

  if user[7] == 1:
    return await callback.answer("حسابك محظور!", show_alert=True)

  ad_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="🔗 اضغط هنا لفتح الإعلان", url=MONETAG_LINK)],
          [
              InlineKeyboardButton(
                  text="✅ تأكيد مشاهدة الإعلان", callback_data="confirm_ad"
              )
          ],
          [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")],
      ]
  )

  await callback.message.edit_text(
      "📺 **قسم مشاهدة الإعلانات اليومية:**\n\n"
      "1️⃣ اضغط على زر (فتح الإعلان).\n"
      "2️⃣ انتظر قليلاً في صفحة الإعلان ثم عُد إلى هنا.\n"
      "3️⃣ اضغط على (تأكيد مشاهدة الإعلان) لتستلم رصيدك.",
      reply_markup=ad_kb,
  )
  await callback.answer()


@dp.callback_query(F.data == "confirm_ad")
async def confirm_ad_handler(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  user = get_user(user_id)

  if user[7] == 1:
    return await callback.answer("حسابك محظور!", show_alert=True)

  current_time = time.time()
  last_click = user[5]
  click_streak = user[6]

  if current_time - last_click < 6:
    click_streak += 1
    if click_streak >= 3:
      cursor.execute(
          "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
      )
      conn.commit()
      await callback.message.edit_text(
          "🚨 **تم اكتشاف نشاط روبوت (Auto-Clicker) أو نقر وهمي!**\n\n"
          "تم حظرك نهائياً من استخدام البوت لمخالفة القوانين."
      )
      return
    else:
      cursor.execute(
          "UPDATE users SET click_streak = ? WHERE user_id = ?",
          (click_streak, user_id),
      )
      conn.commit()
      await callback.answer(
          "⚠️ تحذير: أنت تنقر بسرعة كبيرة جداً! انتظر قليلاً.", show_alert=True
      )
      return
  else:
    click_streak = 0

  new_balance = user[1] + 0.5
  new_ads = user[2] + 1

  cursor.execute(
      "UPDATE users SET balance = ?, ads_today = ?, last_click_time = ?,"
      " click_streak = ? WHERE user_id = ?",
      (new_balance, new_ads, current_time, click_streak, user_id),
  )
  conn.commit()

  await callback.answer("🎉 تم احتساب الإعلان بنجاح وأُضيف الرصيد!", show_alert=True)
  await callback.message.edit_text(
      f"📊 **إحصائياتك اليومية:**\n"
      f"• رصيدك الحالي: **${new_balance:.2f} / $200.00**\n"
      f"• الإعلانات المشاهدة اليوم: {new_ads}/10\n\n"
      f"واصل العمل يومياً لإتمام مدة الـ 60 يوماً والوصول للهدف!",
      reply_markup=main_menu(),
  )


@dp.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
  user = get_user(callback.from_user.id)
  if user[7] == 1:
    return

  text = (
      f"👤 **لوحة معلومات حسابك:**\n\n"
      f"💰 الرصيد المجمع: **${user[1]:.2f} / $200.00**\n"
      f"👥 عدد الإحالات: **{user[3]} / 25**\n"
      f"📺 إعلانات اليوم: {user[2]}/10\n\n"
      f"📌 ملاحظة: زر السحب يتطلب إتمام الشرطين معاً."
  )
  await callback.message.edit_text(text, reply_markup=back_to_home())
  await callback.answer()


@dp.callback_query(F.data == "referral")
async def referral_handler(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  user = get_user(user_id)
  if user[7] == 1:
    return

  bot_info = await bot.get_me()
  ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

  text = (
      f"👥 **نظام دعوة الأصدقاء (الأرباح المضاعفة):**\n\n"
      f"• شارك رابطك أدناه مع أصدقائك وفي المجموعات العربية.\n"
      f"• شرط سحب الأرباح هو تجميع **25 إحالة نشطة**.\n\n"
      f"🔗 **رابط الدعوة الخاص بك:**\n`{ref_link}`"
  )
  await callback.message.edit_text(text, reply_markup=back_to_home())
  await callback.answer()


@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: types.CallbackQuery):
  user = get_user(callback.from_user.id)
  if user[7] == 1:
    return

  balance = user[1]
  referrals = user[3]

  if balance < 200 or referrals < 25:
    await callback.answer(
        f"❌ لم تستوفِ الشروط بعد!\nالرصيد: {balance}/200$ | الإحالات:"
        f" {referrals}/25",
        show_alert=True,
    )
    return

  await callback.message.edit_text(
      "✅ **مبروك لقد أتممت كافة الشروط بنجاح!**\n\n"
      "أرسل الآن عنوان محفظتك (USDT / Payeer / Binance ID) لإتمام عملية التحويل الوهمية."
  )
  await callback.answer()


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
