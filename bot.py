import logging
import aiosqlite
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

GENDER, AGE, HOBBY, LOCATION, PHOTO, DESCRIPTION, MATCHING, EDIT_PROFILE_DESCRIPTION = range(8)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def get_db_connection():
    try:
        return await aiosqlite.connect('database.db')
    except aiosqlite.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None

async def user_already_registered(user_id):
    conn = await get_db_connection()
    if not conn:
        return False
    async with conn:
        async with conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            user_exists = await cursor.fetchone() is not None
    return user_exists

def restricted(func):
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if not await user_already_registered(user_id):
            await update.message.reply_text("Maaf, Anda belum terdaftar. Silakan mulai dengan /start.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if await user_already_registered(user_id):
        await update.message.reply_text("Selamat datang kembali! Anda sudah terdaftar.")
    else:
        reply_keyboard = [[KeyboardButton('Pria'), KeyboardButton('Wanita')]]
        await update.message.reply_text(
            'Halo! Silakan pilih jenis kelamin Anda.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return GENDER

async def gender(update: Update, context: CallbackContext):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text('Berapa usia Anda?')
    return AGE

async def age(update: Update, context: CallbackContext):
    try:
        age = int(update.message.text)
        if age <= 0:
            raise ValueError("Umur harus lebih besar dari 0.")
        context.user_data['age'] = age
        await update.message.reply_text('Apa hobi Anda?')
        return HOBBY
    except ValueError:
        await update.message.reply_text('Harap masukkan usia yang valid.')
        return AGE

async def hobby(update: Update, context: CallbackContext):
    context.user_data['hobby'] = update.message.text
    await update.message.reply_text('Dimana lokasi Anda? Kirimkan lokasi Anda saat ini, silakan.')
    return LOCATION

async def location(update: Update, context: CallbackContext):
    location = update.message.location
    if not location:
        await update.message.reply_text('Lokasi tidak valid. Harap kirimkan lokasi Anda.')
        return LOCATION
    context.user_data['location'] = (location.latitude, location.longitude)
    await update.message.reply_text('Terima kasih! Silakan unggah foto profil Anda sekarang.')
    return PHOTO

async def photo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"profile_photos/{user_id}.jpg"
    await photo_file.download(photo_path)
    context.user_data['photo_path'] = photo_path
    await update.message.reply_text('Foto profil Anda telah diunggah. Silakan tambahkan deskripsi profil Anda sekarang.')
    return DESCRIPTION

async def description(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data['description'] = update.message.text

    user_data = {
        'user_id': user_id,
        'gender': context.user_data['gender'],
        'age': context.user_data['age'],
        'hobby': context.user_data['hobby'],
        'location': context.user_data['location'],
        'photo_path': context.user_data['photo_path'],
        'description': context.user_data['description']
    }
    await save_user_data(user_data)

    await update.message.reply_text('Deskripsi profil Anda telah ditambahkan. Profil Anda telah disimpan.')
    await update.message.reply_text('Mulai mencari pasangan?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

async def save_user_data(user_data):
    conn = await get_db_connection()
    if not conn:
        return
    async with conn:
        await conn.execute("""
            INSERT INTO users (user_id, gender, age, hobby, location, photo_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_data['user_id'], user_data['gender'], user_data['age'], user_data['hobby'], str(user_data['location']), user_data['photo_path'], user_data['description']))
        await conn.commit()

async def start_matching(update: Update, context: CallbackContext):
    reply_keyboard = [[KeyboardButton('Suka'), KeyboardButton('Tidak Suka')]]
    await update.message.reply_text(
        'Saya telah menemukan pasangan potensial untuk Anda. Apakah Anda tertarik?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return MATCHING

async def choose_matching(update: Update, context: CallbackContext):
    choice = update.message.text
    if choice not in ['Suka', 'Tidak Suka']:
        await update.message.reply_text('Pilihan tidak valid. Silakan pilih "Suka" atau "Tidak Suka".')
        return MATCHING

    if choice == 'Suka':
        await update.message.reply_text('Anda menyukai pasangan ini! Selamat!')
    else:
        await update.message.reply_text('Anda tidak tertarik dengan pasangan ini. Coba yang lain ya!')

    await update.message.reply_text('Apakah Anda ingin mencari pasangan lagi?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

async def view_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    profile_data = await get_user_profile(user_id)
    if profile_data:
        await update.message.reply_text(f"Profil Anda:\n{profile_data}")
    else:
        await update.message.reply_text("Profil Anda kosong.")


async def get_user_profile(user_id):
    conn = await get_db_connection()
    if not conn:
        return None
    async with conn:
        async with conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            user_profile = await cursor.fetchone()
    return user_profile

@restricted
async def edit_profile(update: Update, context: CallbackContext):
    await update.message.reply_text("Silakan tambahkan informasi profil Anda.")
    return EDIT_PROFILE_DESCRIPTION

async def save_profile_description(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    profile_description = update.message.text
    context.user_data['description'] = profile_description

    conn = await get_db_connection()
    if not conn:
        return
    async with conn:
        await conn.execute("UPDATE users SET description=? WHERE user_id=?", (profile_description, user_id))
        await conn.commit()

    await update.message.reply_text("Deskripsi profil Anda telah diperbarui.")

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Proses dibatalkan. Sampai jumpa!')
    return ConversationHandler.END

if __name__ == '__main__':
    import asyncio
    async def setup_db():
        conn = await get_db_connection()
        if conn:
            async with conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        gender TEXT,
                        age INTEGER,
                        hobby TEXT,
                        location TEXT,
                        photo_path TEXT,
                        description TEXT,
                        registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await conn.commit()

    asyncio.run(setup_db())

    application = Application.builder().token('YOUR_BOT_TOKEN').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            HOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, hobby)],
            LOCATION: [MessageHandler(filters.LOCATION, location)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            MATCHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_matching)],
            EDIT_PROFILE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_profile_description)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    ))

    application.run_polling()
