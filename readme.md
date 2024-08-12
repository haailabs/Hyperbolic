# SafuBot: Your Crypto Safety Companion

SafuBot is a Telegram bot that helps users navigate the cryptocurrency world safely. It checks addresses and domains for potential threats and offers AI-powered advice on cryptocurrency security.

## Features

- Check cryptocurrency addresses for scam associations
- Verify domains for potential threats
- AI-powered Q&A for crypto security advice

## Commands

- `/address <address>` - Check if an address is associated with scams
- `/domain <domain>` - Check if a domain is associated with scams
- `/ask <question>` - Ask about crypto security or past exploits
- `/help` - Display available commands

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `HYPERBOLIC_API_KEY`
4. Run the bot: `python main.py`

## Deployment

The bot is designed to run on a Flask server with a webhook for Telegram updates.

## Security Note

This bot uses a local SQLite database for scam checks. Ensure the database is regularly updated for accurate results.
