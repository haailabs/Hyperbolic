import os
import json
import telebot
from flask import Flask, request, abort
from dotenv import load_dotenv
import sqlite3
from urllib.parse import quote
import openai
import asyncio

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "No bot token found. Set the TELEGRAM_BOT_TOKEN environment variable.")

HYPERBOLIC_API_KEY = os.getenv('HYPERBOLIC_API_KEY')
if not HYPERBOLIC_API_KEY:
    raise ValueError("No Hyperbolic API key found. Set the HYPERBOLIC_API_KEY environment variable.")

# Initialize Hyperbolic
client = openai.OpenAI(
    api_key=HYPERBOLIC_API_KEY,
    base_url="https://api.hyperbolic.xyz/v1",
)

# Initialize bot and Flask app
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Welcome message
WELCOME_MESSAGE = """
Welcome to SafuBot!

Available commands:
/address <address> - Check if a cryptocurrency address is associated with scams.
/domain <domain> - Check if a domain is associated with scams.
/ask <question> - Ask a question about security or past exploits.
/help - Display this help message.
"""



@bot.message_handler(commands=['ask'])
def ask_question(message):
    try:
        question = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        bot.reply_to(message, "Please provide a question. Usage: /ask <your question>")
        return

    response = asyncio.run(get_hyperbolic_response(question))
    bot.reply_to(message, response)


def normalize_domain(domain):
    """Normalize the domain by removing 'https://', 'http://', 'www.' and converting to lowercase."""
    domain = domain.lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.replace('www.', '')
    return domain.split('/')[0]  # Remove any path after the domain


def check_address(address):
    """Check if an address is in the database and return associated domains if any."""
    conn = sqlite3.connect('scam_check.db')
    cursor = conn.cursor()

    cursor.execute('SELECT EXISTS(SELECT 1 FROM addresses WHERE address = ?)',
                   (address, ))
    exists = cursor.fetchone()[0]

    associated_domains = []
    if exists:
        cursor.execute(
            '''
            SELECT domains.domain
            FROM domains
            JOIN domain_address_mapping ON domains.id = domain_address_mapping.domain_id
            JOIN addresses ON addresses.id = domain_address_mapping.address_id
            WHERE addresses.address = ?
        ''', (address, ))
        associated_domains = [row[0] for row in cursor.fetchall()]

    conn.close()
    return exists, associated_domains


def check_domain(domain):
    """Check if a domain is in the database and return associated addresses if any."""
    conn = sqlite3.connect('scam_check.db')
    cursor = conn.cursor()

    cursor.execute('SELECT EXISTS(SELECT 1 FROM domains WHERE domain = ?)',
                   (domain, ))
    exists = cursor.fetchone()[0]

    associated_addresses = []
    if exists:
        cursor.execute(
            '''
            SELECT addresses.address
            FROM addresses
            JOIN domain_address_mapping ON addresses.id = domain_address_mapping.address_id
            JOIN domains ON domains.id = domain_address_mapping.domain_id
            WHERE domains.domain = ?
        ''', (domain, ))
        associated_addresses = [row[0] for row in cursor.fetchall()]

    conn.close()
    return exists, associated_addresses


# Webhook route for Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(
            request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)


# Command handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, WELCOME_MESSAGE)


@bot.message_handler(commands=['address'])
def check_address_command(message):
    try:
        address = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        bot.reply_to(
            message,
            "Please provide an address to check. Usage: /address <address>")
        return

    is_scam, domains = check_address(address)
    if is_scam:
        response = f"⚠️ WARNING: The address {address} is associated with scams.\n"
        if domains:
            response += f"Associated scam domains: {', '.join(domains)}"
        else:
            response += "No specific domains are associated with this address in our database."
    else:
        response = f"✅ The address {address} is not found in our scam database."

    bot.reply_to(message, response)


@bot.message_handler(commands=['domain'])
def check_domain_command(message):
    try:
        domain = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        bot.reply_to(
            message,
            "Please provide a domain to check. Usage: /domain <domain>")
        return

    normalized_domain = normalize_domain(domain)
    is_scam, addresses = check_domain(normalized_domain)
    if is_scam:
        response = f"⚠️ WARNING: The domain {normalized_domain} is associated with scams.\n"
        if addresses:
            response += f"Associated scam addresses: {', '.join(addresses)}"
        else:
            response += "No specific addresses are associated with this domain in our database."
    else:
        response = f"✅ The domain {normalized_domain} is not found in our scam database."

    bot.reply_to(message, response)

async def get_hyperbolic_response(question):
    system_content = """You are an AI assistant specializing in cryptocurrency security and scam prevention. 
    Provide accurate and helpful information about staying safe in the crypto world. 
    If asked about specific addresses or domains, remind users to use the /address or /domain commands for checking against the scam database.
    
    
    """

    chat_completion = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    response = chat_completion.choices[0].message.content
    return response

# Main Flask app route
@app.route('/')
def home():
    return "ScamBot is running!"


if __name__ == "__main__":
    # Remove any existing webhooks
    bot.remove_webhook()

    # Set the webhook URL (adjust this URL based on your hosting environment)
    webhook_url = f'https://yourURL.com/webhook'

    bot.set_webhook(url=webhook_url)
    print(f"Webhook set to {webhook_url}")

    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
