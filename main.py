import os
import json
import time
import threading
import re
import requests
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telegram import (
    Update,
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
)

BOT_TOKEN = '7997768946:AAH_8jjar9uU1IDcPav3XRazFQQwXFt1tqo'

DATA_FILE = "price_data.json"
FETCH_INTERVAL = 600  # every 10 minutes

# --- Fetch price from Polymarket ---
def get_price():
    url = "https://polymarket.com/event/us-x-iran-nuclear-deal-in-2025"
    response = requests.get(url)
    if response.status_code == 200:
        match = re.search(r'"outcomePrices":\s*\[\s*"([^"]+)"', response.text)
        if match:
            return round(float(match.group(1)) * 100, 2)
    return None

# --- Data storage ---
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def fetch_and_store_price():
    price = get_price()
    if price is not None:
        data = load_data()
        timestamp = int(time.time())
        data.append({"time": timestamp, "price": price})
        # Keep only last 6 hours of data
        cutoff = timestamp - 6 * 60 * 60
        data = [d for d in data if d["time"] >= cutoff]
        save_data(data)
        print(f"Saved price {price} at {datetime.fromtimestamp(timestamp)}")
    else:
        print("Failed to fetch price")

    threading.Timer(FETCH_INTERVAL, fetch_and_store_price).start()

# --- Graph plotting ---
def plot_prices():
    data = load_data()
    if not data:
        return None

    times = [datetime.fromtimestamp(d["time"]) for d in data]
    prices = [d["price"] for d in data]

    plt.figure(figsize=(8, 4))
    plt.plot(times, prices, marker='o')
    plt.title("Polymarket Price - Last 6 Hours")
    plt.xlabel("Time")
    plt.ylabel("Price × 100")
    plt.grid(True)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    img_path = "price_plot.png"
    plt.savefig(img_path)
    plt.close()
    return img_path

# --- Command handlers ---
def price_command(update: Update, context: CallbackContext):
    price = get_price()
    if price is not None:
        update.message.reply_text(f"{price}")
    else:
        update.message.reply_text("Price not available.")

def hello_command(update: Update, context: CallbackContext):
    update.message.reply_text("Hello!")

def graph_command(update: Update, context: CallbackContext):
    img_path = plot_prices()
    if img_path:
        with open(img_path, "rb") as f:
            update.message.reply_photo(photo=InputFile(f))
    else:
        update.message.reply_text("No graph data available yet.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Available commands:\n"
        "/price - Get current price\n"
        "/graph - Show price graph\n"
        "/hello - Say hello\n"
        "/help - Show help message\n"
        "/menu - Show quick buttons"
    )

def menu_command(update: Update, context: CallbackContext):
    start_command(update, context)

def start_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📈 Price", callback_data="price")],
        [InlineKeyboardButton("🖼️ Graph", callback_data="graph")],
        [InlineKeyboardButton("👋 Hello", callback_data="hello")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose an option:", reply_markup=reply_markup)

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "price":
        price = get_price()
        if price is not None:
            query.edit_message_text(text=f"{price}")
        else:
            query.edit_message_text(text="Price not available.")

    elif query.data == "graph":
        img_path = plot_prices()
        if img_path:
            with open(img_path, "rb") as f:
                query.delete_message()
                query.message.reply_photo(photo=InputFile(f))
        else:
            query.edit_message_text(text="No graph data available yet.")

    elif query.data == "hello":
        query.edit_message_text(text="Hello!")

# --- Main ---
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("price", price_command))
    dp.add_handler(CommandHandler("hello", hello_command))
    dp.add_handler(CommandHandler("graph", graph_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("menu", menu_command))
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(button_callback))

    # Set visible command menu in Telegram
    default_commands = [
        BotCommand("start", "Show menu with buttons"),
        BotCommand("price", "Get current price"),
        BotCommand("graph", "Show 6h price graph"),
        BotCommand("hello", "Say hello"),
        BotCommand("help", "Show help message"),
        BotCommand("menu", "Show quick action buttons"),
    ]
    updater.bot.set_my_commands(default_commands)

    # Start background price fetcher
    fetch_and_store_price()

    print("Bot is running. Send /start to try it.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
