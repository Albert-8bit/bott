import os
import json
import time
import threading
import re
import requests
from datetime import datetime

# --- matplotlib backend fix for Railway (headless) ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "price_data.json"
FETCH_INTERVAL = 600  # 10 minutes

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# --- Fetch price from Polymarket ---
def get_price():
    url = "https://polymarket.com/event/us-x-iran-nuclear-deal-in-2025"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(r'"outcomePrices":\s*\[\s*"([^"]+)"', response.text)
        if match:
            return round(float(match.group(1)) * 100, 2)
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None

# --- Data storage ---
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

def fetch_and_store_price():
    try:
        price = get_price()
        if price is not None:
            data = load_data()
            timestamp = int(time.time())
            data.append({"time": timestamp, "price": price})
            # Keep last 6 hours of data
            cutoff = timestamp - 6 * 60 * 60
            data = [d for d in data if d["time"] >= cutoff]
            save_data(data)
            print(f"Saved price {price} at {datetime.fromtimestamp(timestamp)}")
        else:
            print("Failed to fetch price")
    except Exception as e:
        print(f"Error in fetch_and_store_price: {e}")
    
    # Schedule next fetch
    threading.Timer(FETCH_INTERVAL, fetch_and_store_price).start()

# --- Plot price graph ---
def plot_prices():
    try:
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
    except Exception as e:
        print(f"Error generating plot: {e}")
        return None

# --- Telegram command handlers ---
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = get_price()
        if price is not None:
            await update.message.reply_text(f"📈 Current price: {price}")
        else:
            await update.message.reply_text("Price not available.")
    except Exception as e:
        print(f"Error in price_command: {e}")
        await update.message.reply_text("An error occurred.")

async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Hello!")
    except Exception as e:
        print(f"Error in hello_command: {e}")

async def graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        img_path = plot_prices()
        if img_path:
            with open(img_path, "rb") as f:
                await update.message.reply_photo(photo=InputFile(f))
            os.remove(img_path)
        else:
            await update.message.reply_text("No graph data available yet.")
    except Exception as e:
        print(f"Error in graph_command: {e}")
        await update.message.reply_text("Error generating graph.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "Available commands:\n"
            "/price - Get current price\n"
            "/graph - Show price graph\n"
            "/hello - Say hello\n"
            "/help - Show help message\n"
            "/menu - Show quick buttons"
        )
    except Exception as e:
        print(f"Error in help_command: {e}")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("📈 Price", callback_data="price")],
            [InlineKeyboardButton("🖼️ Graph", callback_data="graph")],
            [InlineKeyboardButton("👋 Hello", callback_data="hello")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose an option:", reply_markup=reply_markup)
    except Exception as e:
        print(f"Error in start_command: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        if query.data == "price":
            price = get_price()
            if price is not None:
                await query.edit_message_text(text=f"📈 {price}")
            else:
                await query.edit_message_text(text="Price not available.")
        elif query.data == "graph":
            img_path = plot_prices()
            if img_path:
                with open(img_path, "rb") as f:
                    await query.delete_message()
                    await query.message.reply_photo(photo=InputFile(f))
                os.remove(img_path)
            else:
                await query.edit_message_text(text="No graph data available yet.")
        elif query.data == "hello":
            await query.edit_message_text(text="Hello!")
    except Exception as e:
        print(f"Error in button_callback: {e}")

# --- Main entry point ---
async def main():
    try:
        # Ensure data file exists
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w') as f:
                json.dump([], f)

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("price", price_command))
        app.add_handler(CommandHandler("graph", graph_command))
        app.add_handler(CommandHandler("hello", hello_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("menu", menu_command))
        app.add_handler(CallbackQueryHandler(button_callback))

        await app.bot.set_my_commands([
            BotCommand("start", "Show menu with buttons"),
            BotCommand("price", "Get current price"),
            BotCommand("graph", "Show 6h price graph"),
            BotCommand("hello", "Say hello"),
            BotCommand("help", "Show help message"),
            BotCommand("menu", "Show quick action buttons"),
        ])

        # Start price fetching in a separate thread
        threading.Thread(target=fetch_and_store_price, daemon=True).start()
        print("Bot is running. Send /start to try it.")
        await app.run_polling()
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
