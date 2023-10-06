# This script creates a csv file with the file names and ids of all files in a Google Drive folder.
# To be used on process_files.py
# A file_list.csv file is created in the data folder.
# A web browser will open to authenticate the Google Drive account.

import csv

from google_auth import authenticate_and_get_drive

from settings import GOOGLE_FOLDER_ID

drive, gauth = authenticate_and_get_drive()

file_titles = set()

file_list = drive.ListFile({'q': f"'{GOOGLE_FOLDER_ID}' in parents and trashed=false"}).GetList()
with open('file_list.csv', 'w') as f:
    fieldnames = ['title', 'mimeType', 'id']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for f in file_list:
        if f["title"] in file_titles:
            continue
        file_titles.add(f["title"])
        writer.writerow({'title': f["title"], 'mimeType': f["mimeType"], 'id': f["id"]})
        print(f'title: {f["title"]} mimeType: {f["mimeType"]} id: {f["id"]}')
    
