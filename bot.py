import logging
import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

GENDER, AGE, HOBBY, LOCATION, PHOTO, DESCRIPTION, MATCHING, EDIT_PROFILE_DESCRIPTION = range(8)

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('''
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
conn.commit()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def user_already_registered(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return c.fetchone() is not None

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_already_registered(user_id):
        update.message.reply_text("Selamat datang kembali! Anda sudah terdaftar.")
    else:
        reply_keyboard = [[KeyboardButton('Pria'), KeyboardButton('Wanita')]]
        update.message.reply_text(
            'Halo! Silakan pilih jenis kelamin Anda.',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return GENDER

def gender(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data['gender'] = update.message.text
    update.message.reply_text('Berapa usia Anda?')
    return AGE

def age(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data['age'] = update.message.text
    update.message.reply_text('Apa hobi Anda?')
    return HOBBY

def hobby(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    context.user_data['hobby'] = update.message.text
    update.message.reply_text('Dimana lokasi Anda? Kirimkan lokasi Anda saat ini, silakan.')
    return LOCATION

def location(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    location = update.message.location
    context.user_data['location'] = (location.latitude, location.longitude)
    update.message.reply_text('Terima kasih! Silakan unggah foto profil Anda sekarang.')
    return PHOTO

def photo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    photo_file = update.message.photo[-1].get_file()
    photo_path = f"profile_photos/{user_id}.jpg"
    photo_file.download(photo_path)
    context.user_data['photo_path'] = photo_path
    update.message.reply_text('Foto profil Anda telah diunggah. Silakan tambahkan deskripsi profil Anda sekarang.')
    return DESCRIPTION

def description(update: Update, context: CallbackContext):
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
    save_user_data(user_data) 
    
    update.message.reply_text('Deskripsi profil Anda telah ditambahkan. Profil Anda telah disimpan.')
    update.message.reply_text('Mulai mencari pasangan?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def save_user_data(user_data):
    c.execute("""
        INSERT INTO users (user_id, gender, age, hobby, location, photo_path, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_data['user_id'], user_data['gender'], user_data['age'], user_data['hobby'], user_data['location'], user_data['photo_path'], user_data['description']))
    conn.commit()

def start_matching(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reply_keyboard = [[KeyboardButton('Suka'), KeyboardButton('Tidak Suka')]]
    update.message.reply_text(
        'Saya telah menemukan pasangan potensial untuk Anda. Apakah Anda tertarik?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return MATCHING

def choose_matching(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    choice = update.message.text
    
    if choice == 'Suka':
        update.message.reply_text('Anda menyukai pasangan ini! Selamat!')
    else:
        update.message.reply_text('Anda tidak tertarik dengan pasangan ini. Coba yang lain ya!')
    
    update.message.reply_text('Apakah Anda ingin mencari pasangan lagi?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def view_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    profile_data = get_user_profile(user_id)  
    if profile_data:
        update.message.reply_text(f"Profil Anda:\n{profile_data}")
    else:
        update.message.reply_text("Profil Anda kosong.")

def get_user_profile(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return c.fetchone()

@restricted
def edit_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    update.message.reply_text("Silakan tambahkan informasi profil Anda.")
    return EDIT_PROFILE_DESCRIPTION

def save_profile_description(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    profile_description = update.message.text
    context.user_data['description'] = profile_description
    
    c.execute("UPDATE users SET description=? WHERE user_id=?", (profile_description, user_id))
    conn.commit()
    
    update.message.reply_text("Deskripsi profil Anda telah diperbarui.")

def restricted(func):
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if not user_already_registered(user_id):
            update.message.reply_text("Maaf, Anda belum terdaftar. Silakan mulai dengan /start.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Proses dibatalkan. Sampai jumpa!')
    return ConversationHandler.END

if __name__ == '__main__':
    updater = Updater(token='TOKEN_BOT_ANDA', use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(Filters.text & ~Filters.command, gender)],
            AGE: [MessageHandler(Filters.text & ~Filters.command, age)],
            HOBBY: [MessageHandler(Filters.text & ~Filters.command, hobby)],
            LOCATION: [MessageHandler(Filters.location, location)],
            PHOTO: [MessageHandler(Filters.photo, photo)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, description)],
            MATCHING: [
                MessageHandler(Filters.text & ~Filters.command, start_matching),
                MessageHandler(Filters.text & ~Filters.command, choose_matching)
            ],
            EDIT_PROFILE_DESCRIPTION: [
                MessageHandler(Filters.text & ~Filters.command, save_profile_description)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    ))
    dispatcher.add_handler(CommandHandler('view_profile', view_profile))
    dispatcher.add_handler(CommandHandler('edit_profile', edit_profile))
    updater.start_polling()
    updater.idle()
