from flask import Flask, request, jsonify
import requests
import os
import logging
import sys

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Essential checks for deployment
if not TELEGRAM_TOKEN:
    logging.error("TELEGRAM_TOKEN environment variable is not set. Exiting.")
    sys.exit(1)
if not CHAT_ID:
    logging.error("TELEGRAM_CHAT_ID environment variable is not set. Exiting.")
    sys.exit(1)

@app.route('/', methods=['POST'])
def webhook():
    if not request.is_json:
        logging.warning("Received non-JSON request from %s.", request.remote_addr)
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        data = request.get_json()
        logging.info(f"Received webhook data from {request.remote_addr}: {data}")

        message_content = "No message content extracted from webhook."

        if isinstance(data, dict):
            if 'text' in data and isinstance(data['text'], str):
                message_content = data['text']
            elif 'message' in data and isinstance(data['message'], dict) and 'text' in data['message']:
                message_content = data['message']['text']
            elif 'message' in data and isinstance(data['message'], str):
                message_content = data['message']
            elif 'alert' in data and isinstance(data['alert'], dict) and 'description' in data['alert']:
                message_content = data['alert']['description']
            elif 'alert' in data and isinstance(data['alert'], str):
                message_content = data['alert']

        if message_content == "No message content extracted from webhook.":
            logging.warning("Could not extract a specific message from webhook. Sending default alert.")

        telegram_api_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': CHAT_ID,
            'text': message_content
        }

        logging.info(f"Attempting to send message to Telegram chat ID {CHAT_ID}...")
        response = requests.post(telegram_api_url, data=payload)
        response.raise_for_status()

        telegram_response_json = response.json()
        if telegram_response_json.get('ok'):
            logging.info(f"Alert sent successfully to Telegram chat ID {CHAT_ID}: '{message_content}'")
            return jsonify({"status": "success", "message": "Alert sent to Telegram"}), 200
        else:
            error_description = telegram_response_json.get('description', 'Unknown Telegram API error')
            logging.error(f"Telegram API reported an error: {error_description} (Code: {telegram_response_json.get('error_code')})")
            return jsonify({"status": "error", "message": "Telegram API error", "details": error_description}), 200

    except requests.exceptions.RequestException as e:
        logging.error(f"Network or API error when sending to Telegram: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to send to Telegram due to network/API issue"}), 500
    except ValueError:
        logging.error("Invalid JSON data received.", exc_info=True)
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400
    except Exception as e:
        logging.error(f"An unexpected internal server error occurred: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal server error occurred"}), 500

if __name__ == '__main__':
    logging.info("Starting Flask application for local development...")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
