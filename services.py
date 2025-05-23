import json
import logging
import os


from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import SERVICE_ACCOUNT_FILE, CREDENTIALS_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)

def get_drive_service():
    """Initialize and return Google Drive API service."""
    try:
        # Try service account auth first
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            return build('drive', 'v3', credentials=credentials)
        
        # Fall back to OAuth
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
        
        credentials = None
        if os.path.exists(TOKEN_FILE):
            credentials = Credentials.from_authorized_user_info(
                json.loads(open(TOKEN_FILE).read()), SCOPES)
        
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(TOKEN_FILE, 'w') as token:
                token.write(credentials.to_json())
                
        return build('drive', 'v3', credentials=credentials)
    
    except Exception as e:
        logger.error(f"Error setting up Drive service: {e}")
        raise

def get_sheets_service():
    """Initialize and return Google Sheets API service."""
    try:
        # Similar auth logic as drive service
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            return build('sheets', 'v4', credentials=credentials)
        
        # Fall back to OAuth using the same credentials as Drive
        from google.oauth2.credentials import Credentials
        
        credentials = None
        if os.path.exists(TOKEN_FILE):
            credentials = Credentials.from_authorized_user_info(
                json.loads(open(TOKEN_FILE).read()), 
                ['https://www.googleapis.com/auth/spreadsheets']
            )
            
        return build('sheets', 'v4', credentials=credentials)
    
    except Exception as e:
        logger.error(f"Error setting up Sheets service: {e}")
        raise
