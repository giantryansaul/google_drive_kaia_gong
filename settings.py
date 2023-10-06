import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

USER_LIST_PICKLE = os.path.join(DATA_DIR, 'user_list.pickle')
USER_LIST_CSV = os.path.join(DATA_DIR, 'user_list.csv')


GOOGLE_FOLDER_ID = os.environ.get('GOOGLE_FOLDER_ID')

GONG_API_URL = 'https://us-27353.api.gong.io'
# GONG_API_URL = 'http://localhost:8000' # 

GONG_KEY = os.environ.get('GONG_KEY')
GONG_SECRET = os.environ.get('GONG_SECRET')
DEFAULT_USER_ID = os.environ.get('DEFAULT_USER_ID')
DEFAULT_USER_NAME = os.environ.get('DEFAULT_USER_NAME')

INPUT_LIST = os.path.join(DATA_DIR, 'file_list.csv')
COMPLETED_LIST_CSV = os.path.join(DATA_DIR, 'completed_list.csv')
SHORT_VIDEO_LIST_CSV = os.path.join(DATA_DIR, 'short_video_list.csv')
ERROR_VIDEO_LIST_CSV = os.path.join(DATA_DIR, 'error_video_list.csv')
CREDENTIALS_FILE = os.path.join(DATA_DIR, 'credentials.json')
LOG_FILE = os.path.join(LOG_DIR, 'process_files.log')

NUM_THREADS = 5
MAX_ITERATIONS = 0