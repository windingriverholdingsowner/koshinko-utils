import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Google API settings
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
TOKEN_FILE = os.getenv('TOKEN_FILE')

# Image naming patterns
IMAGE_PREFIX_PATTERN = os.getenv('IMAGE_PREFIX_PATTERN')
COLUMN1_IDENTIFIER = os.getenv('COLUMN1_IDENTIFIER')
COLUMN2_IDENTIFIER = os.getenv('COLUMN2_IDENTIFIER')
COLUMN3_IDENTIFIER = os.getenv('COLUMN3_IDENTIFIER')
ADDITIONAL_IDENTIFIERS = os.getenv('ADDITIONAL_IDENTIFIERS', '').split(',')

# Display settings
THUMBNAIL_SIZE = int(os.getenv('THUMBNAIL_SIZE', 100))
USE_BASE64_THUMBNAILS = os.getenv('USE_BASE64_THUMBNAILS', 'True').lower() == 'true'
MAX_THUMBNAILS = int(os.getenv('MAX_THUMBNAILS', 100))

# Google Drive folder IDs
SOURCE_FOLDER_ID = os.getenv('SOURCE_FOLDER_ID')
OUTPUT_FOLDER_ID = os.getenv('OUTPUT_FOLDER_ID')
OUTPUT_SPREADSHEET_NAME = os.getenv('OUTPUT_SPREADSHEET_NAME')

# Debug mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
