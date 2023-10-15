
# Google Drive (Upload from Kaia) to Gong Data Transfer

## Setup

### Install Python Requirements


### Install ffmpeg


### Google Auth Setup

- [Documentation](https://docs.iterative.ai/PyDrive2/quickstart/#authentication)
- Create a file called `client_secrets.json` in the root of the project with the JSON from the Google API Console

### Google Drive Setup

- From the Google Driver folder you want to get data from, copy the ID from the share URL.

### Environment Variables

Recommend setting up a .env file locally with the following variables:
- `GOOGLE_DRIVE_FOLDER_ID`: The ID of the Google Drive folder to get data from.
- `GONG_KEY`: The API key for the Gong API.
- `GONG_SECRET`: The API secret for the Gong API.
- `DEFAULT_USER_ID`: The default user ID to use for the Gong API.
- `DEFAULT_USER_NAME`: The default user name to use for the Gong API.

## Usage

This project is broken up into 3 scripts:
- `create_file_list.py`: Creates a list of files from Google Driver to process.
- `create_user_list.py`: Creates a list of users from Gong to use for reference IDs in the upload.
- `process_files.py`: Processes the files from Google Drive and uploads them to Gong.

Environment variables can be set in a `.env` file in the root of the project by running `source .env`.

### Create file list

```bash
python3 create_file_list.py
```

### Create user list
    
```bash
python3 create_user_list.py
```

### Process files

```bash
python3 process_files.py
```

## Testing

### Run test server
This can be used for uploading data to a mock Gong server.

```bash
python3.10 -m uvicorn mock_gong_server:app --reload
```

Set `GONG_API_URL = 'http://localhost:8000'`