from flask import Flask
from threading import Thread
import os
import sys
import logging
from datetime import datetime

app = Flask('')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def home():
    logging.info("Home route accessed")
    return "Hello. I am alive!"

def run():
    logging.info("Starting Flask app")
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    logging.info("Starting keep_alive thread")
    t = Thread(target=run)
    t.start()

@app.route('/restart')
def restart():
    logging.info("Restart route accessed")
    os.execv(sys.executable, ['python'] + sys.argv)
    return "Restarting..."

if __name__ == "__main__":
    logging.info("keep_alive.py started")
    keep_alive()
