import logging
import os
import asyncio
from pathlib import Path
from typing import Dict, Any

import aiosqlite
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# Konfigurasi Logging
# Mengatur format log untuk menyertakan waktu, nama logger, level log, dan pesan.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Mengatur level log untuk library HTTPX agar tidak terlalu verbose.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Definisi State untuk ConversationHandler
# State ini merepresentasikan langkah-langkah dalam alur percakapan registrasi dan matching.
(
    GENDER,
    AGE,
    HOBBY,
    LOCATION,
    PHOTO,
    DESCRIPTION,
    MENU,
    MATCHING,
    EDIT_PROFILE,
) = range(9)

DATABASE_FILE = "dating_bot_2025.db"


async def setup_database(app: Application):
    """
    Inisialisasi koneksi database dan membuat tabel jika belum ada.
    Fungsi ini dijalankan sekali saat bot startup menggunakan `post_init`.
    """
    db = await aiosqlite.connect(DATABASE_FILE)
    # Membuat tabel 'users' untuk menyimpan data profil pengguna.
    # user_id dibuat UNIQUE untuk memastikan tidak ada duplikasi.
    # photo_id digunakan untuk menyimpan file_id dari Telegram, bukan path file lokal.
    # latitude dan longitude disimpan sebagai REAL untuk query geografis di masa depan.
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            hobby TEXT,
            latitude REAL,
            longitude REAL,
            photo_id TEXT,
            description TEXT,
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Membuat tabel 'swipes' untuk melacak interaksi antar pengguna.
    # PRIMARY KEY (swiper_id, swiped_id) mencegah satu pengguna swipe orang yang sama berkali-kali.
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS swipes (
            swiper_id INTEGER NOT NULL,
            swiped_id INTEGER NOT NULL,
            action TEXT NOT NULL, -- 'like' or 'dislike'
            swipe_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (swiper_id, swiped_id)
        )
        """
    )
    await db.commit()
    # Menyimpan objek koneksi database ke dalam context bot untuk digunakan di seluruh aplikasi.
    app.bot_data["db"] = db
    logger.info("Database connected and tables are ready.")


async def close_database(app: Application):
    """Menutup koneksi database saat bot berhenti."""
    await app.bot_data["db"].close()
    logger.info("Database connection closed.")


async def user_exists(user_id: int, db: aiosqlite.Connection) -> bool:
    """Memeriksa apakah pengguna sudah terdaftar di database."""
    async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
        return await cursor.fetchone() is not None


# --- Alur Registrasi ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai bot. Memeriksa apakah pengguna sudah terdaftar atau memulai proses registrasi."""
    user = update.effective_user
    db = context.bot_data["db"]

    if await user_exists(user.id, db):
        await update.message.reply_text(
            "Selamat datang kembali! 🎉\n\n"
            "Gunakan menu di bawah untuk mulai mencari pasangan atau mengelola profil Anda.",
            reply_markup=main_menu_keyboard(),
        )
        return MENU
    else:
        await update.message.reply_text(
            f"Halo, {user.first_name}! Selamat datang di bot kencan. Mari kita buat profil Anda.\n\n"
            "Silakan pilih jenis kelamin Anda.",
            reply_markup=ReplyKeyboardMarkup([["Pria", "Wanita"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return GENDER


async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan jenis kelamin dan meminta usia."""
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("Hebat! Sekarang, berapa usia Anda?", reply_markup=ReplyKeyboardRemove())
    return AGE


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan usia dan meminta hobi."""
    try:
        age_value = int(update.message.text)
        if not 18 <= age_value <= 99:
            raise ValueError("Usia harus antara 18 dan 99.")
        context.user_data["age"] = age_value
        await update.message.reply_text("OK. Apa hobi utama Anda? (Contoh: Membaca, Olahraga, Nonton Film)")
        return HOBBY
    except ValueError:
        await update.message.reply_text("Mohon masukkan usia yang valid (angka antara 18-99).")
        return AGE


async def hobby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan hobi dan meminta lokasi."""
    context.user_data["hobby"] = update.message.text
    location_keyboard = [[KeyboardButton("Bagikan Lokasi Saat Ini", request_location=True)]]
    await update.message.reply_text(
        "Hobi yang menarik! Sekarang, silakan bagikan lokasi Anda agar kami bisa menemukan pasangan di sekitar Anda.",
        reply_markup=ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return LOCATION


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan lokasi dan meminta foto."""
    user_location = update.message.location
    context.user_data["latitude"] = user_location.latitude
    context.user_data["longitude"] = user_location.longitude
    await update.message.reply_text(
        "Lokasi diterima! Terakhir, unggah foto terbaik Anda untuk profil.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHOTO


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan file_id foto dan meminta deskripsi."""
    # Menyimpan file_id, bukan men-download fotonya. Ini lebih efisien dan portabel.
    context.user_data["photo_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("Foto yang bagus! Sekarang tulis deskripsi singkat tentang diri Anda.")
    return DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan deskripsi, menyimpan seluruh profil ke DB, dan masuk ke menu utama."""
    user_id = update.effective_user.id
    context.user_data["description"] = update.message.text
    db = context.bot_data["db"]

    # Mengumpulkan semua data dari context.user_data
    user_profile: Dict[str, Any] = {
        "user_id": user_id,
        "gender": context.user_data.get("gender"),
        "age": context.user_data.get("age"),
        "hobby": context.user_data.get("hobby"),
        "latitude": context.user_data.get("latitude"),
        "longitude": context.user_data.get("longitude"),
        "photo_id": context.user_data.get("photo_id"),
        "description": context.user_data.get("description"),
    }

    try:
        # Menyimpan data pengguna ke database
        await db.execute(
            """
            INSERT INTO users (user_id, gender, age, hobby, latitude, longitude, photo_id, description)
            VALUES (:user_id, :gender, :age, :hobby, :latitude, :longitude, :photo_id, :description)
            """,
            user_profile,
        )
        await db.commit()
        logger.info(f"User profile for {user_id} saved successfully.")

        await update.message.reply_text(
            "Pendaftaran selesai! Profil Anda telah dibuat. ✨\n\n"
            "Sekarang Anda bisa mulai mencari pasangan atau melihat profil Anda.",
            reply_markup=main_menu_keyboard(),
        )
        # Membersihkan user_data setelah registrasi selesai
        context.user_data.clear()
        return MENU

    except aiosqlite.Error as e:
        logger.error(f"Database error on saving profile for {user_id}: {e}")
        await update.message.reply_text(
            "Maaf, terjadi kesalahan saat menyimpan profil Anda. Silakan coba lagi nanti."
        )
        return ConversationHandler.END


# --- Menu Utama dan Fungsinya ---

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Membuat keyboard untuk menu utama."""
    return ReplyKeyboardMarkup(
        [["Cari Pasangan 💘"], ["Profil Saya 👤", "Edit Profil 📝"]], resize_keyboard=True
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler untuk navigasi dari menu utama."""
    choice = update.message.text
    if choice == "Cari Pasangan 💘":
        return await find_match(update, context)
    elif choice == "Profil Saya �":
        return await my_profile(update, context)
    elif choice == "Edit Profil 📝":
        await update.message.reply_text("Apa yang ingin Anda ubah?", reply_markup=edit_profile_keyboard())
        return EDIT_PROFILE
    else:
        await update.message.reply_text("Pilihan tidak valid. Silakan gunakan tombol di bawah.")
        return MENU


async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menampilkan profil pengguna saat ini."""
    user_id = update.effective_user.id
    db = context.bot_data["db"]

    async with db.execute("SELECT gender, age, hobby, description, photo_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
        profile = await cursor.fetchone()

    if profile:
        gender, age, hobby, description, photo_id = profile
        caption = (
            f"<b>Profil Anda</b>\n\n"
            f"<b>🚻 Gender:</b> {gender}\n"
            f"<b>🎂 Usia:</b> {age} tahun\n"
            f"<b>🎨 Hobi:</b> {hobby}\n\n"
            f"<b>📝 Deskripsi:</b>\n{description}"
        )
        await update.message.reply_photo(photo=photo_id, caption=caption, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("Profil Anda tidak ditemukan. Mungkin Anda belum mendaftar? /start")

    return MENU # Kembali ke menu utama setelah menampilkan profil

# --- Fitur Matching ---

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mencari dan menampilkan calon pasangan."""
    user_id = update.effective_user.id
    db = context.bot_data["db"]

    # Mencari pengguna lain yang belum pernah di-swipe oleh pengguna saat ini.
    # Diurutkan secara acak untuk variasi.
    query = """
        SELECT user_id, gender, age, hobby, description, photo_id
        FROM users
        WHERE user_id != ? AND user_id NOT IN (
            SELECT swiped_id FROM swipes WHERE swiper_id = ?
        )
        ORDER BY RANDOM()
        LIMIT 1
    """
    async with db.execute(query, (user_id, user_id)) as cursor:
        potential_match = await cursor.fetchone()

    if potential_match:
        match_id, gender, age, hobby, description, photo_id = potential_match
        context.user_data["potential_match_id"] = match_id

        caption = (
            f"<b>🚻 {gender}, {age} tahun</b>\n"
            f"<b>🎨 Hobi:</b> {hobby}\n\n"
            f"<b>📝 Deskripsi:</b>\n{description}"
        )
        
        # Menggunakan Inline Keyboard untuk aksi Suka/Tidak Suka
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("❌ Tidak Suka", callback_data=f"match_dislike_{match_id}"),
                    InlineKeyboardButton("❤️ Suka", callback_data=f"match_like_{match_id}"),
                ]
            ]
        )
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
        return MATCHING

    else:
        await update.message.reply_text(
            "Sepertinya sudah tidak ada calon pasangan lagi untuk saat ini. Coba lagi nanti! 😊",
            reply_markup=main_menu_keyboard(),
        )
        return MENU


async def match_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pilihan Suka/Tidak Suka dari Inline Keyboard."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db = context.bot_data["db"]
    
    # Parsing callback_data: "match_like_12345" atau "match_dislike_12345"
    action, match_id_str = query.data.split("_")[1:]
    match_id = int(match_id_str)

    try:
        # Mencatat aksi swipe ke database
        await db.execute(
            "INSERT INTO swipes (swiper_id, swiped_id, action) VALUES (?, ?, ?)",
            (user_id, match_id, action),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        # Pengguna sudah pernah swipe orang ini, abaikan.
        logger.warning(f"User {user_id} tried to swipe {match_id} again.")
        await query.edit_message_text("Anda sudah pernah berinteraksi dengan profil ini.")
        return await find_match(update, context) # Langsung cari yang baru

    # Mengedit pesan asli untuk menghilangkan tombol
    original_caption = query.message.caption
    if action == "like":
        await query.edit_message_caption(caption=f"{original_caption}\n\n--- (Anda menyukai profil ini ❤️) ---", parse_mode=ParseMode.HTML)
        # Cek apakah ada mutual like
        async with db.execute("SELECT 1 FROM swipes WHERE swiper_id = ? AND swiped_id = ? AND action = 'like'", (match_id, user_id)) as cursor:
            is_mutual = await cursor.fetchone()
        
        if is_mutual:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Selamat! Anda dan pengguna lain saling suka! 🎉 Kalian sekarang match!",
            )
            await context.bot.send_message(
                chat_id=match_id,
                text=f"Selamat! Anda dan pengguna lain saling suka! 🎉 Kalian sekarang match!",
            )
    else: # dislike
        await query.edit_message_caption(caption=f"{original_caption}\n\n--- (Anda melewati profil ini ❌) ---", parse_mode=ParseMode.HTML)

    # Otomatis mencari pasangan berikutnya
    return await find_match(update, context)


# --- Fitur Edit Profil ---

def edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Membuat keyboard untuk menu edit profil."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ubah Deskripsi", callback_data="edit_description")],
        [InlineKeyboardButton("Ubah Hobi", callback_data="edit_hobby")],
        [InlineKeyboardButton("Kembali ke Menu", callback_data="edit_cancel")]
    ])

async def edit_profile_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pilihan dari menu edit profil."""
    query = update.callback_query
    await query.answer()

    choice = query.data.split('_')[1] # "description", "hobby", atau "cancel"
    
    if choice == "description":
        await query.message.reply_text("Silakan kirim deskripsi baru Anda.")
        return DESCRIPTION # Menggunakan kembali state dari registrasi
    elif choice == "hobby":
        await query.message.reply_text("Silakan kirim hobi baru Anda.")
        return HOBBY # Menggunakan kembali state dari registrasi
    elif choice == "cancel":
        await query.message.edit_text("Edit dibatalkan.", reply_markup=None)
        await query.message.reply_text("Anda kembali di menu utama.", reply_markup=main_menu_keyboard())
        return MENU
    return EDIT_PROFILE

async def save_new_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan deskripsi profil yang baru."""
    user_id = update.effective_user.id
    new_description = update.message.text
    db = context.bot_data["db"]

    await db.execute("UPDATE users SET description = ? WHERE user_id = ?", (new_description, user_id))
    await db.commit()

    await update.message.reply_text("Deskripsi profil Anda telah berhasil diperbarui!", reply_markup=main_menu_keyboard())
    return MENU

async def save_new_hobby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan hobi yang baru."""
    user_id = update.effective_user.id
    new_hobby = update.message.text
    db = context.bot_data["db"]

    await db.execute("UPDATE users SET hobby = ? WHERE user_id = ?", (new_hobby, user_id))
    await db.commit()

    await update.message.reply_text("Hobi Anda telah berhasil diperbarui!", reply_markup=main_menu_keyboard())
    return MENU


# --- Fungsi Umum dan Fallback ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan proses saat ini (misal: registrasi) dan kembali ke awal."""
    await update.message.reply_text(
        "Proses dibatalkan. Ketik /start untuk memulai lagi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah yang tidak dikenal."""
    await update.message.reply_text("Maaf, saya tidak mengerti perintah itu. Coba /start.")


def main() -> None:
    """Fungsi utama untuk menjalankan bot."""
    # Mengambil token dari environment variable. Lebih aman daripada hardcoding.
    token = os.getenv("TELEGRAM_TOKEN", "GANTI_DENGAN_TOKEN_BOT_ANDA")
    if token == "GANTI_DENGAN_TOKEN_BOT_ANDA":
        logger.error("TELEGRAM_TOKEN tidak diatur. Mohon atur environment variable atau ganti di dalam kode.")
        return

    # Menggunakan Application.builder() untuk membuat aplikasi bot.
    application = (
        Application.builder()
        .token(token)
        .post_init(setup_database) # Menjalankan setup DB saat bot mulai
        .post_shutdown(close_database) # Menutup koneksi DB saat bot berhenti
        .build()
    )

    # ConversationHandler untuk alur registrasi dan menu utama
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # States untuk registrasi
            GENDER: [MessageHandler(filters.Regex("^(Pria|Wanita)$"), gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            HOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, hobby)],
            LOCATION: [MessageHandler(filters.LOCATION, location)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            
            # State untuk menu utama
            MENU: [
                MessageHandler(filters.Regex("^(Cari Pasangan 💘)$"), find_match),
                MessageHandler(filters.Regex("^(Profil Saya 👤)$"), my_profile),
                MessageHandler(filters.Regex("^(Edit Profil 📝)$"), edit_profile_choice),
            ],
            
            # State untuk matching
            MATCHING: [CallbackQueryHandler(match_choice, pattern="^match_")],

            # State untuk edit profil
            EDIT_PROFILE: [CallbackQueryHandler(edit_profile_choice, pattern="^edit_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Mengizinkan pengguna untuk kembali ke menu utama dari state mana pun
        map_to_parent={
            MENU: MENU, # Kembali ke menu dari state edit atau matching
            ConversationHandler.END: ConversationHandler.END
        }
    )
    
    # ConversationHandler terpisah untuk proses edit, agar lebih modular
    edit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_profile_choice, pattern="^edit_")],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_description)],
            HOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_hobby)],
        },
        fallbacks=[CallbackQueryHandler(lambda u,c: MENU, pattern="^edit_cancel")],
        map_to_parent={
            MENU: MENU,
            ConversationHandler.END: MENU
        }
    )

    # Gabungan handler utama
    main_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GENDER: [MessageHandler(filters.Regex("^(Pria|Wanita)$"), gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            HOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, hobby)],
            LOCATION: [MessageHandler(filters.LOCATION, location)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            MENU: [
                MessageHandler(filters.Regex("^(Cari Pasangan 💘)$"), find_match),
                MessageHandler(filters.Regex("^(Profil Saya 👤)$"), my_profile),
                edit_conv_handler, # Nested conversation untuk edit
            ],
            MATCHING: [CallbackQueryHandler(match_choice, pattern="^match_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


    application.add_handler(main_conv_handler)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Menjalankan bot
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
�
