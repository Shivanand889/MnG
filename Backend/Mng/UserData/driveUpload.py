import io, os, pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_service():
   
    pass

def upload_to_drive(file_obj, filename, mimetype="image/jpeg", folder_id=None):
    

    pass
