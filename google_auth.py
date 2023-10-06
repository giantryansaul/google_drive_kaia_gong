import os

from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth

from settings import CREDENTIALS_FILE

def authenticate_and_get_drive():
    gauth = GoogleAuth()
    gauth.settings['get_refresh_token'] = True

    if os.path.exists(CREDENTIALS_FILE):
        gauth.LoadCredentialsFile(CREDENTIALS_FILE)

    if not gauth.credentials or gauth.credentials.invalid:
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile(CREDENTIALS_FILE)

    if gauth.access_token_expired:
        gauth.Refresh()
        gauth.SaveCredentialsFile(CREDENTIALS_FILE)

    drive = GoogleDrive(gauth)
    return drive, gauth