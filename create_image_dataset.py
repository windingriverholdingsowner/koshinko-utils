import os
import re
import base64
import io
import logging

from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd


from config import *
from services import get_drive_service, get_sheets_service


logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_files_in_folder(drive_service, folder_id):
    """List all files in the specified Google Drive folder."""
    results = []
    page_token = None
    
    while True:
        response = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType)',
            pageToken=page_token
        ).execute()
        
        results.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        
        if not page_token:
            break
    
    if DEBUG:
        print(f"Found {len(results)} files in folder {folder_id}")
        
    return results

def download_file_as_base64(drive_service, file_id):
    """Download a file from Drive and convert it to base64."""
    request = drive_service.files().get_media(fileId=file_id)
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    file_content.seek(0)
    return base64.b64encode(file_content.read()).decode('utf-8')

def create_or_get_spreadsheet(drive_service, sheets_service, name, folder_id):
    """Create a new Google Sheet or get an existing one with the given name."""
    # Check if spreadsheet already exists in the folder
    response = drive_service.files().list(
        q=f"name='{name}' and '{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    files = response.get('files', [])
    
    if files:
        # Use existing spreadsheet
        spreadsheet_id = files[0]['id']
        if DEBUG:
            print(f"Using existing spreadsheet: {spreadsheet_id}")
        
        # Clear existing content
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        if sheets:
            sheet_id = sheets[0]['properties']['sheetId']
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "updateCells": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "startColumnIndex": 0
                                },
                                "fields": "userEnteredValue"
                            }
                        }
                    ]
                }
            ).execute()
    else:
        # Create new spreadsheet
        spreadsheet = {
            'properties': {
                'title': name
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        
        # Move to correct folder
        file = drive_service.files().get(
            fileId=spreadsheet_id, 
            fields='parents'
        ).execute()
        
        previous_parents = ",".join(file.get('parents', []))
        drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        
        if DEBUG:
            print(f"Created new spreadsheet: {spreadsheet_id}")
    
    return spreadsheet_id

def group_files_by_prefix(files):
    """Group files based on their prefix from the filename pattern."""
    # Create regex pattern for matching filenames
    base_identifiers = [COLUMN1_IDENTIFIER, COLUMN2_IDENTIFIER, COLUMN3_IDENTIFIER]
    all_identifiers = base_identifiers + ADDITIONAL_IDENTIFIERS
    
    # Create alternation of all possible identifiers for the regex
    identifiers_pattern = '|'.join(all_identifiers)
    
    # Pattern to match: prefix followed by underscore, then any of the identifiers, optional text, then file extension
    pattern = f"^({IMAGE_PREFIX_PATTERN})_.*({identifiers_pattern}).*\\.(jpe?g|png|gif|bmp|tiff?)$"
    regex = re.compile(pattern, re.IGNORECASE)
    
    grouped_files = {}
    for file in files:
        filename = file['name']
        match = regex.match(filename)
        
        if match:
            prefix = match.group(1)
            identifier = None
            
            # Determine which identifier is in the filename
            for id_type in all_identifiers:
                if re.search(f"_{id_type}", filename.lower()):
                    identifier = id_type
                    break
            
            if not identifier:
                if DEBUG:
                    print(f"Warning: Matched prefix but couldn't determine identifier type for {filename}")
                continue
                
            if prefix not in grouped_files:
                grouped_files[prefix] = {}
            
            # Store file info with its identifier type
            grouped_files[prefix][identifier] = {
                'id': file['id'],
                'name': file['name']
            }
    
    if DEBUG:
        print(f"Grouped files into {len(grouped_files)} sets")
        
    return grouped_files

def create_image_cell_value(drive_service, file_info):
    file_id = file_info['id']
    file_name = file_info['name']
    
    if USE_BASE64_THUMBNAILS:
        logger.info(f"Downloading and encoding {file_name} (ID: {file_id}) as base64")
        base64_data = download_file_as_base64(drive_service, file_id)
        return f'=IMAGE("data:image/jpeg;base64,{base64_data}", 1)'
    else:
        logger.info(f"Using Drive URL for {file_name} (ID: {file_id})")
        return f'=IMAGE("https://drive.google.com/uc?id={file_id}", 1)'

# def create_image_and_link_cells(drive_service, file_info):
#     """Return a tuple: (thumbnail image cell, hyperlink cell)."""
#     file_id = file_info['id']
#     url = f"https://drive.google.com/uc?id={file_id}"

#     # Ensure the file is accessible for IMAGE formula to work
#     try:
#         drive_service.permissions().create(
#             fileId=file_id,
#             body={'type': 'anyone', 'role': 'reader'},
#             fields='id'
#         ).execute()
#     except Exception as e:
#         logger.warning(f"Could not set public permission for file {file_info['name']}: {e}")

#     image_cell = f'=IMAGE("{url}", 1)'
#     link_cell = f'=HYPERLINK("{url}", "Full Size")'
#     return image_cell, link_cell
# def create_image_and_link_cells(drive_service, file_info):
#     """Return a tuple: (thumbnail image cell, hyperlink with filename)."""
#     file_id = file_info['id']
#     file_name = file_info['name']
#     url = f"https://drive.google.com/uc?id={file_id}"

#     try:
#         drive_service.permissions().create(
#             fileId=file_id,
#             body={'type': 'anyone', 'role': 'reader'},
#             fields='id'
#         ).execute()
#     except Exception as e:
#         logger.warning(f"Could not set public permission for file {file_name}: {e}")

#     image_cell = f'=IMAGE("{url}", 1)'
#     link_cell = f'=HYPERLINK("{url}", "{file_name}")'
#     return image_cell, link_cell


# def prepare_spreadsheet_data(drive_service, grouped_files):
#     """Prepare data for the spreadsheet with image formulas."""
#     # Define the columns based on configuration
#     base_columns = ['Prefix', COLUMN1_IDENTIFIER.capitalize(), COLUMN2_IDENTIFIER.capitalize(), COLUMN3_IDENTIFIER.capitalize()]
#     additional_columns = [identifier.capitalize() for identifier in ADDITIONAL_IDENTIFIERS if identifier]
#     all_columns = base_columns + additional_columns
    
#     # Prepare header row
#     data = [all_columns]
    
#     # Prepare data rows
#     count = 0
#     for prefix, files_dict in grouped_files.items():
#         row = [prefix]
        
#         # Add main columns (front, back, detail)
#         for identifier in [COLUMN1_IDENTIFIER, COLUMN2_IDENTIFIER, COLUMN3_IDENTIFIER]:
#             if identifier in files_dict:
#                 file_info = files_dict[identifier]
#                 image_cell, link_cell = create_image_and_link_cells(drive_service, file_info)
#                 #image_formula = create_image_cell_value(drive_service, file_info)
#                 row.append(link_cell)
#             else:
#                 row.append("")
        
#         # Add additional columns if any
#         for identifier in ADDITIONAL_IDENTIFIERS:
#             if identifier and identifier in files_dict:
#                 file_info = files_dict[identifier]
#                 image_cell, link_cell = create_image_and_link_cells(drive_service, file_info)
#                 #image_formula = create_image_cell_value(drive_service, file_info)
#                 row.append(link_cell)
#             else:
#                 row.append("")
        
#         data.append(row)
#         count += 1
        
#         if count >= MAX_THUMBNAILS:
#             if DEBUG:
#                 print(f"Reached maximum thumbnail limit of {MAX_THUMBNAILS}")
#             break
    
#     return data

def prepare_spreadsheet_data(drive_service, grouped_files):
    """Prepare data for the spreadsheet with image formulas."""
    # Define the columns based on configuration
    base_columns = ['Prefix', COLUMN1_IDENTIFIER.capitalize(), COLUMN2_IDENTIFIER.capitalize(), COLUMN3_IDENTIFIER.capitalize()]
    additional_columns = [identifier.capitalize() for identifier in ADDITIONAL_IDENTIFIERS if identifier]
    all_columns = base_columns + additional_columns
    
    # Prepare header row
    data = [all_columns]
    
    # Prepare data rows
    count = 0
    for prefix, files_dict in grouped_files.items():
        row = [prefix]
        
        # Add main columns (front, back, detail)
        for identifier in [COLUMN1_IDENTIFIER, COLUMN2_IDENTIFIER, COLUMN3_IDENTIFIER]:
            if identifier in files_dict:
                file_info = files_dict[identifier]
                image_formula = create_image_cell_value(drive_service, file_info)
                row.append(image_formula)
            else:
                row.append("")
        
        # Add additional columns if any
        for identifier in ADDITIONAL_IDENTIFIERS:
            if identifier and identifier in files_dict:
                file_info = files_dict[identifier]
                image_formula = create_image_cell_value(drive_service, file_info)
                row.append(image_formula)
            else:
                row.append("")
        
        data.append(row)
        count += 1
        
        if count >= MAX_THUMBNAILS:
            if DEBUG:
                print(f"Reached maximum thumbnail limit of {MAX_THUMBNAILS}")
            break
    
    return data

# def prepare_spreadsheet_data(drive_service, grouped_files):
#     """Prepare data for the spreadsheet with thumbnails and clickable links."""
#     # Combine identifiers
#     base_identifiers = [COLUMN1_IDENTIFIER, COLUMN2_IDENTIFIER, COLUMN3_IDENTIFIER]
#     all_identifiers = base_identifiers + [id for id in ADDITIONAL_IDENTIFIERS if id]

#     # Header: Prefix, then two columns per identifier (Image + Link)
#     headers = ['Prefix']
#     for identifier in all_identifiers:
#         headers.append(f"{identifier.capitalize()} Image")
#         headers.append(f"{identifier.capitalize()} Link")

#     data = [headers]

#     count = 0
#     for prefix, files_dict in grouped_files.items():
#         row = [prefix]

#         for identifier in all_identifiers:
#             if identifier in files_dict:
#                 file_info = files_dict[identifier]
#                 try:
#                     image_cell, link_cell = create_image_and_link_cells(drive_service, file_info)
#                 except Exception as e:
#                     logger.warning(f"Failed to create cells for {file_info['name']}: {e}")
#                     image_cell, link_cell = "", ""
#                 row.append(image_cell)
#                 row.append(link_cell)
#             else:
#                 row.extend(["", ""])

#         data.append(row)
#         count += 1

#         if count >= MAX_THUMBNAILS:
#             if DEBUG:
#                 logger.info(f"Reached maximum thumbnail limit of {MAX_THUMBNAILS}")
#             break

#     return data


def update_spreadsheet(sheets_service, spreadsheet_id, data):
    """Update the spreadsheet with the prepared data."""
    sheet_range = f"A1:{chr(65 + len(data[0]) - 1)}{len(data)}"
    
    body = {
        'values': data
    }
    
    result = sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption='USER_ENTERED',  # Important for formulas to work
        body=body
    ).execute()
    
    # Adjust row heights to accommodate images
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']
    
    requests = [
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'ROWS',
                    'startIndex': 1,  # Skip header row
                    'endIndex': len(data)
                },
                'properties': {
                    'pixelSize': THUMBNAIL_SIZE + 20  # Add some padding
                },
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 1,  # Skip prefix column
                    'endIndex': len(data[0])
                },
                'properties': {
                    'pixelSize': THUMBNAIL_SIZE + 20  # Add some padding
                },
                'fields': 'pixelSize'
            }
        }
    ]
    
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()
    
    if DEBUG:
        print(f"Updated {result.get('updatedCells')} cells in spreadsheet")
    
    return result

def main():
    """Main function to orchestrate the process."""
    try:
        print("Starting Google Drive to Sheets image transfer...")
        
        # Initialize services
        drive_service = get_drive_service()
        sheets_service = get_sheets_service()
        
        # List files in source folder
        files = list_files_in_folder(drive_service, SOURCE_FOLDER_ID)
        
        # Group files by prefix and identifier
        grouped_files = group_files_by_prefix(files)
        
        # Create or get spreadsheet
        spreadsheet_id = create_or_get_spreadsheet(
            drive_service, 
            sheets_service, 
            OUTPUT_SPREADSHEET_NAME, 
            OUTPUT_FOLDER_ID
        )
        
        # Prepare data for spreadsheet
        logger.debug("Preparing data for spreadsheet...")
        data = prepare_spreadsheet_data(drive_service, grouped_files)
        logger.debug(f"Prepared {len(data) - 1} rows of data for spreadsheet.")
        
        # Update spreadsheet with image formulas
        logger.debug("Updating spreadsheet with image data...")
        update_spreadsheet(sheets_service, spreadsheet_id, data)
        logger.debug("Spreadsheet updated successfully.")
        
        # Get the spreadsheet URL to return to user
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        logger.info(f"Successfully processed {len(grouped_files)} image sets.")
        logger.info(f"Spreadsheet available at: {spreadsheet_url}")

        return spreadsheet_url
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import json  # Needed for credentials handling
    main()