import logging
import sqlite3
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, File
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, \
    CallbackQueryHandler, CallbackContext

GENDER, AGE, HOBBY, LOCATION, PHOTO, DESCRIPTION, MATCHING = range(7)

def start(update, context):
    reply_keyboard = [[KeyboardButton('Pria'), KeyboardButton('Wanita')]]
    update.message.reply_text(
        'Halo! Selamat datang di bot dating. Silakan pilih jenis kelamin Anda.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return GENDER

def gender(update, context):
    user = update.message.from_user
    context.user_data['gender'] = update.message.text
    update.message.reply_text('Berapa usia Anda?')
    return AGE

def age(update, context):
    user = update.message.from_user
    context.user_data['age'] = update.message.text
    update.message.reply_text('Apa hobi Anda?')
    return HOBBY

def hobby(update, context):
    user = update.message.from_user
    context.user_data['hobby'] = update.message.text
    update.message.reply_text('Dimana lokasi Anda? Kirimkan lokasi Anda saat ini, silakan.')
    return LOCATION

def location(update, context):
    user = update.message.from_user
    location = update.message.location
    context.user_data['location'] = (location.latitude, location.longitude)
    update.message.reply_text('Terima kasih! Silakan unggah foto profil Anda sekarang.')
    return PHOTO


def photo(update, context):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('profile_photos/{}.jpg'.format(user.id))
    update.message.reply_text('Foto profil Anda telah diunggah. Silakan tambahkan deskripsi profil Anda sekarang.')
    return DESCRIPTION


def description(update, context):
    user = update.message.from_user
    context.user_data['description'] = update.message.text
    update.message.reply_text('Deskripsi profil Anda telah ditambahkan. Profil Anda telah disimpan.')
    update.message.reply_text('Mulai mencari pasangan?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def start_matching(update, context):
    user = update.message.from_user
    reply_keyboard = [[KeyboardButton('Suka'), KeyboardButton('Tidak Suka')]]
    update.message.reply_text(
        'Saya telah menemukan pasangan potensial untuk Anda. Apakah Anda tertarik?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return MATCHING


def choose_matching(update, context):
    user = update.message.from_user
    choice = update.message.text
    
    if choice == 'Suka':
        update.message.reply_text('Anda menyukai pasangan ini! Selamat!')
    else:
        update.message.reply_text('Anda tidak tertarik dengan pasangan ini. Coba yang lain ya!')
    
    update.message.reply_text('Apakah Anda ingin mencari pasangan lagi?', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ya'), KeyboardButton('Tidak')]], one_time_keyboard=True))
    return MATCHING

def cancel(update, context):
    user = update.message.from_user
    update.message.reply_text('Proses dibatalkan. Sampai jumpa!')
    return ConversationHandler.END

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    updater = Updater(token='TOKEN_BOT_ANDA', use_context=True)
    dispatcher = updater.dispatcher
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            gender TEXT,
            age TEXT,
            hobby TEXT,
            location TEXT,
            photo_path TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    
    # Daftar command handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    
    # Daftar message handler
    conversation_handler = ConversationHandler(
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
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conversation_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
