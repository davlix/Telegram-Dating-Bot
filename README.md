# Telegram Dating Bot (2025 Version)

This is a Telegram dating bot project built with Python using the latest version of the `python-telegram-bot` library (v20+). This bot allows users to register, create a profile, and find matches based on a "Like" or "Dislike" swipe system.

---

## ✨ Key Features

-   **👤 Complete Profile Registration:** Users can sign up by providing the following information:
    -   Gender
    -   Age
    -   Hobby
    -   Location (using Telegram's native feature)
    -   Profile Picture
    -   Self-Description
-   **💘 Matching System:**
    -   Displays other user profiles one by one.
    -   Inline "❤️ Like" and "❌ Dislike" buttons for easy interaction.
    -   The bot will not show profiles that have already been seen.
-   **🎉 Mutual Like Notifications:** If two users like each other, the bot will automatically notify both of them that they have a match.
-   **📝 Profile Management:**
    -   Users can view their own profile at any time.
    -   Features to edit their description and hobby after registration.
-   **💾 Local Database:** Uses **SQLite** via `aiosqlite` for persistent and fast data storage.
-   **🤖 Modern Interface:** Utilizes `ConversationHandler` for a structured conversation flow and `InlineKeyboardMarkup` for a better user experience.

---

## 🛠️ Tech Stack

-   **Python 3.8+**
-   **python-telegram-bot v20+**
-   **aiosqlite** for asynchronous database operations
-   **SQLite** as the database

---

## 🚀 How to Run the Bot

### 1. Prerequisites

-   Python 3.8 or newer.
-   A Telegram account.
-   **A Telegram Bot Token.** You can get one from [@BotFather](https://t.me/BotFather) on Telegram.

### 2. Installation

1.  **Download the Code**
    Copy the `telegram_bot_2025.py` file to your local directory.

2.  **Install Dependencies**
    Open a terminal or command prompt in the project directory and run the following command:
    ```bash
    pip install "python-telegram-bot[ext]" aiosqlite
    ```

### 3. Configuration

1.  **Set Your Bot Token**
    The most recommended way is to use an environment variable.

    -   **On Linux/macOS:**
        ```bash
        export TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
        ```
    -   **On Windows (CMD):**
        ```bash
        set TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
        ```
    -   **On Windows (PowerShell):**
        ```powershell
        $env:TELEGRAM_TOKEN="YOUR_TOKEN_HERE"
        ```

    *Alternative (not recommended for production):* You can directly change the following line of code in the `.py` file:
    ```python
    token = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ```

### 4. Run the Bot

After all dependencies are installed and the token is set, run the bot with the command:
```bash
python your_bot_file.py
```

Your bot is now active and ready to receive messages on Telegram!

---

## 🤖 Bot Commands

-   `/start` - Starts the interaction with the bot, either for registration or to go to the main menu.
-   `/cancel` - Cancels the current process (e.g., during registration).

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
