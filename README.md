# Telegram Bot for Matching Application

This Telegram bot application allows users to register, create profiles, and find potential matches based on their preferences.

## Features

- **User Authentication:** Users can register and log in to the bot using their Telegram account.
- **Profile Management:** Users can set up their profiles including gender, age, hobbies, location, photo, and description.
- **Search and Filtering:** Users can search for potential matches based on specified criteria.
- **Notifications:** Users receive notifications for new matches or messages.
- **Chat History:** Users can view their chat history with matches.
- **Privacy Settings:** Users can manage privacy settings such as who can view their profile.
- **Database Optimization:** The application uses SQLite for efficient data storage and retrieval.
- **Security Considerations:** Basic security measures are implemented to protect user data.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/davlix/Telegram-Dating-Bot.git
   cd Telegram-Dating-Bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Telegram Bot:
   - Create a bot and get the API token from BotFather.
   - Replace `'TOKEN_BOT_ANDA'` in `main.py` with your bot's API token.

4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage

- Start the bot by sending `/start` to register and set up your profile.
- Use commands like `/view_profile` to view your profile or `/edit_profile` to edit your profile description.
- Use the bot's features to find and interact with potential matches.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
