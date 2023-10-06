# Description: This script downloads the files from the Google Drive folder and uploads them to Gong.
# Usage: python process_files.py

import datetime
import os
import csv
import json
import requests
from queue import Queue
from threading import Thread, Lock
import zipfile
from pathlib import Path
import logging
import pickle
import subprocess
import traceback

from google_auth import authenticate_and_get_drive

from settings import *


def configure_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')

    file_handler = logging.FileHandler(os.path.join(LOG_DIR, datetime.datetime.now().strftime("process_files_%Y%m%d%H%M%S.log")))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = configure_logging()

drive, gauth = authenticate_and_get_drive()

user_map = pickle.load(open(USER_LIST_PICKLE, 'rb'))

def remove_folder(folder_path):
    logger.info(f"Removing folder: {folder_path}")
    os.rmdir(folder_path)

def remove_file(file_path):
    logger.info(f"Removing file: {file_path}")
    os.remove(file_path)

class ThreadSafeCsvWriter:
    def __init__(self, file_name, fieldnames):
        self.file_name = file_name
        self.fieldnames = fieldnames
        self.lock = Lock()
        self.csv_file = open(file_name, 'a', newline='')
        self.writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        if os.path.getsize(file_name) == 0:
            self.writer.writeheader()

    def write_row(self, row_data):
        with self.lock:
            self.writer.writerow(row_data)

    def close(self):
        self.csv_file.close()


class InvalidVideoFileError(Exception):
    pass

def get_video_length(filename):
    result = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{filename}"',
            shell=True).decode()
    try:
        fields = json.loads(result)['streams'][0]
        duration = fields['duration']
        fps      = eval(fields['r_frame_rate'])
    except IndexError:
        raise InvalidVideoFileError
    return duration, fps

def download_file(real_file_id, destination):
    # If the file exists, remove it and download again
    if os.path.exists(destination):
        logger.info(f"ID: {real_file_id} - File already exists, removing: {destination}")
        remove_file(destination)
        # raise Exception("File already exists")
    logger.info(f"ID: {real_file_id} - Downloading file: {real_file_id} to {destination}")
    sample_file = drive.CreateFile({'id': real_file_id})
    sample_file.GetContentFile(destination)

def unpack_file(zip_file_path: str):
    extract_to_path = zip_file_path.replace('.zip', '')
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_path)
    
    folder_path = Path(extract_to_path)
    paths = [str(file) for file in folder_path.glob('**/*') if file.is_file()]

    for value in paths:
        if value.endswith('.json'):
            json_file = value
        elif value.endswith('.mp4'):
            video_file = value

    remove_file(zip_file_path)
    return video_file, json_file, extract_to_path

def load_file_list():
    with open(INPUT_LIST, 'r') as f:
        reader = csv.DictReader(f)
        file_list = [row for row in reader]
    return file_list

def load_processed_list(list_csv):
    try:
        with open(list_csv, 'r') as f:
            reader = csv.DictReader(f)
            completed_list = [row for row in reader]
    except FileNotFoundError:
        completed_list = []
    return completed_list

def create_call_in_gong(unique_id, title, start_time, primary_user_id, party_users, real_file_id):
    # Limit title to 1024 characters
    title = title[:1024]
    logger.info(f"ID: {real_file_id} - Creating call in Gong - UNIQUE_ID: {unique_id} TITLE: {title}")
    request_json = {
            "clientUniqueId": unique_id, 
            "title": title,
            "actualStart": start_time,
            "parties": party_users,
            "primaryUser": primary_user_id,
            "direction": "Inbound",
        }
    logger.debug(f"ID: {real_file_id} - Request JSON: {request_json}")
    response = requests.post(
        f"{GONG_API_URL}/v2/calls",
        auth=(GONG_KEY, GONG_SECRET),
        json=request_json
    )
    if response.status_code >= 400:
        logger.error(f"ID: {real_file_id} - Error creating call in Gong - UNIQUE_ID: {unique_id} TITLE: {title} STATUS_CODE: {response.status_code} RESPONSE: {response.text}")
    response.raise_for_status()
    return response.json()['callId']

class AlreadyUploadedError(Exception):
    pass

def upload_file_to_gong_call(call_id, file_path, real_file_id):
    logger.info(f"ID: {real_file_id} - Uploading file to Gong - CALL_ID: {call_id} FILE: {file_path}")
    response = requests.put(
        f"{GONG_API_URL}/v2/calls/{call_id}/media",
        auth=(GONG_KEY, GONG_SECRET),
        files={"mediaFile": open(file_path, 'rb')}
    )
    if response.status_code >= 400:
        logger.error(f"ID: {real_file_id} - Error uploading file to Gong - CALL_ID: {call_id} FILE: {file_path} STATUS_CODE: {response.status_code} RESPONSE: {response.text}")
        if 'A media file with the same content has been uploaded in the past' in response.text:
            logger.info(f"File already uploaded to Gong - CALL_ID: {call_id} FILE: {file_path}")
            raise AlreadyUploadedError
        else:
            response.raise_for_status()
    url = response.json()['url']
    logger.info(f"ID: {real_file_id} - Uploaded file to Gong - CALL_ID: {call_id} FILE: {file_path} URL: {url}")
    return url

def get_user_id_if_exists(name):
    if name in user_map:
        return user_map[name]
    for key, value in user_map.items():
        if key in name:
            return value
    return None

def create_party_users(participant_names):
    primary_user_id = ""
    party_users = []
    for name in participant_names:
        user_id = get_user_id_if_exists(name)
        primary_user_id = user_id if user_id else primary_user_id
        user_object = {"name": name}
        if user_id:
            user_object["userId"] = user_id
        party_users.append(user_object)
    # If there is no primary user, add the default user
    if not primary_user_id:
        party_users.append({"name": DEFAULT_USER_NAME, "userId": DEFAULT_USER_ID})
        primary_user_id = DEFAULT_USER_ID
    return party_users, primary_user_id

def is_video_short(video_file, real_file_id):
    duration, fps = get_video_length(video_file)
    logger.info(f"ID: {real_file_id} - Video length: {duration} FPS: {fps} - FILE: {video_file}")
    if float(duration) < 60:
        logger.info(f"ID: {real_file_id} - Video is less than 60 seconds, skipping - FILE: {video_file}")
        return True
    return False

def convert_date_time_to_gong_format(date_time):
    date_strings = date_time.split(' ')
    date = date_strings[0]
    time = date_strings[1]
    return f"{date}T{time}Z"

def process_files_to_gong(unique_id, meeting_video_file, info_json, real_file_id):
    # Create the call in Gong
    logger.info(f"ID: {real_file_id} - Upload data to gong - MEETING: {meeting_video_file} INFO: {info_json}")
    with open(info_json, 'r') as f:
        data = json.load(f)

        meeting_title = data['MeetingTitle']
        participant_names = data['ParticpantNames']
        party_users, primary_user_id = create_party_users(participant_names)
        start_time = convert_date_time_to_gong_format(data['StartTime'])

        call_id = create_call_in_gong(
            unique_id=unique_id,
            title=f"{meeting_title} - {', '.join(participant_names)}",
            start_time=start_time,
            primary_user_id=primary_user_id,
            party_users=party_users,
            real_file_id=real_file_id
        )

    # Upload the video to Gong
    url = upload_file_to_gong_call(call_id, meeting_video_file, real_file_id)
    return call_id, url, participant_names
    

def download_and_process_worker(file_queue: Queue, completed_list_writer: ThreadSafeCsvWriter, short_video_list_writer: ThreadSafeCsvWriter, error_video_list_writer: ThreadSafeCsvWriter):
    while True:
        try:
            if gauth.access_token_expired:
                gauth.Refresh()
            logger.info(f"File queue size: {file_queue.qsize()}")
            real_file_id, file_title, zip_file_destination, iterations = file_queue.get()
            logger.info(f"ID: {real_file_id} - Processing file - TITLE: {file_title} ITERATIONS: {iterations}")
            download_file(real_file_id, zip_file_destination)
            logger.info(f"ID: {real_file_id} - Unpacking file - FILE: {zip_file_destination}")
            meeting_file, info_json, extracted_folder_path = unpack_file(zip_file_destination)
            if is_video_short(meeting_file, real_file_id):
                short_video_list_writer.write_row({'id': real_file_id, 'title': file_title})
            else:
                unique_id = f"{real_file_id}-{iterations}-reupload"
                call_id, url, participant_names = process_files_to_gong(unique_id, meeting_file, info_json, real_file_id)
                completed_list_writer.write_row({
                    'id': real_file_id, 
                    'title': file_title, 
                    'call_id': call_id, 
                    'url': url, 
                    'participant_names': '|'.join(participant_names)
                })
            remove_file(meeting_file)
            remove_file(info_json)
            remove_folder(extracted_folder_path)
        except AlreadyUploadedError:
            logger.info(f"ID: {real_file_id} - AlreadyUploadedError - File already uploaded to Gong - FILE: {file_title}")
            error_video_list_writer.write_row({'id': real_file_id, 'title': file_title, 'reason': 'Already uploaded'})
        except InvalidVideoFileError:
            logger.info(f"ID: {real_file_id} - InvalidVideoFileError - Invalid video file, writing to short video list - FILE: {file_title}")
            short_video_list_writer.write_row({'id': real_file_id, 'title': file_title})
        except requests.exceptions.HTTPError as e:
            logger.error(f"ID: {real_file_id} - HTTPError - An error occurred while uploading to Gong - ERROR: {e} - FILE: {file_title} TRACEBACK: {traceback.format_exc()}")
            error_video_list_writer.write_row({'id': real_file_id, 'title': file_title, 'reason': 'Gong upload error'})
        except Exception as e:
            logger.info(f"ID: {real_file_id} - An error occurred for task - ERROR: {e} - FILE: {file_title} TRACEBACK: {traceback.format_exc()}")
            try:
                remove_file(meeting_file)
                remove_file(info_json)
                remove_folder(extracted_folder_path)
            except Exception as e:
                logger.error(f"ID: {real_file_id} - An error occurred while cleaning up files - ERROR: {e} - FILE: {file_title} TRACEBACK: {traceback.format_exc()}")
            if iterations < MAX_ITERATIONS:
                file_queue.put((real_file_id, file_title, zip_file_destination, iterations + 1))
            else:
                logger.info(f"ID: {real_file_id} - Max iterations reached for task - FILE: {file_title}")
                error_video_list_writer.write_row({'id': real_file_id, 'title': file_title, 'reason': 'Max iterations reached'})
        file_queue.task_done()
        logger.info(f"ID: {real_file_id} - Task done - FILE: {file_title}")

def main():
    file_list = load_file_list()
    completed_list = load_processed_list(COMPLETED_LIST_CSV)
    short_video_list = load_processed_list(SHORT_VIDEO_LIST_CSV)
    error_video_list = load_processed_list(ERROR_VIDEO_LIST_CSV)

    completed_list_writer = ThreadSafeCsvWriter(COMPLETED_LIST_CSV, ['id', 'title', 'call_id', 'url', 'participant_names'])
    short_video_list_writer = ThreadSafeCsvWriter(SHORT_VIDEO_LIST_CSV, ['id', 'title'])
    error_video_list_writer = ThreadSafeCsvWriter(ERROR_VIDEO_LIST_CSV, ['id', 'title', 'reason'])

    # Return all files from file_list that do not have an id in completed_list or short_video_list
    file_list = [f for f in file_list if f['id'] not in [c['id'] for c in completed_list]]
    file_list = [f for f in file_list if f['id'] not in [c['id'] for c in short_video_list]]
    file_list = [f for f in file_list if f['id'] not in [c['id'] for c in error_video_list]]
    
    file_queue = Queue()

    try:
        # Load the file queue from the saved file list
        for file_entry in file_list:
            destination = f"dest/{file_entry['title']}"
            file_queue.put((file_entry['id'], file_entry['title'], destination, 0))

        for _ in range(NUM_THREADS):
            t = Thread(target=download_and_process_worker, args=(file_queue, completed_list_writer, short_video_list_writer, error_video_list_writer))
            t.daemon = True
            t.start()

        file_queue.join()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt, stopping threads.")
        completed_list_writer.close()
        short_video_list_writer.close()
        exit()

    completed_list_writer.close()
    short_video_list_writer.close()
    logger.info("All files downloaded and processed.")


if __name__ == "__main__":
    main()