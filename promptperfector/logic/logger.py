import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'debug.log')

def log(msg, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [{level}] {msg}\n")

def log_debug(msg):
    log(msg, 'DEBUG')

def log_info(msg):
    log(msg, 'INFO')

def log_error(msg):
    log(msg, 'ERROR')
