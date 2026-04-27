"""
auto_file_backup.py
21.04.2026

automatically backs up gps log files

Author:
Nilusink
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build, Resource

from types import NoneType
from time import time
import typing as tp
import shutil
import math
import os

from hud_lib import latlon_to_meters

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SOURCE_DIR: str = "./logs"
PROCESSED_DIR: str = "./logs/processed"

if not os.path.exists(PROCESSED_DIR):
    os.mkdir(PROCESSED_DIR)


class FileInfo(tp.TypedDict):
    """file infor returned by Google"""
    id: str
    name: str


class ApiWrapper:
    """wrapper around Google Drive API"""
    creds: Credentials | None = None
    service: Resource | None = None
    folder_id: str = "1W4B7qJMdkd2YVjTn5D1G8tPnS8IjX87n"

    def auth(self) -> tp.Self:
        """get authorization code"""
        if os.path.exists("token.json"):
            from google.oauth2.credentials import Credentials
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secret.json",
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            if not isinstance(self.creds, NoneType):
                with open("token.json", "w") as f:
                    f.write(self.creds.to_json())

        return self

    def start_service(self) -> tp.Self:
        """start session service"""
        if not self.creds:
            self.auth()

        self.service = build("drive", "v3", credentials=self.creds)
        return self

    def upload_file(self, filepath: str) -> FileInfo:
        """upload file to directory"""
        if not os.path.isfile(filepath):
            raise RuntimeError(f"File not found: {filepath}")

        if not self.service:
            self.start_service()

        file_metadata = {
            "name": filepath.replace("\\", "/").split("/")[-1],
            "parents": [self.folder_id]  # drive folder
        }

        media = MediaFileUpload(
            filepath,
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name"
        ).execute()

        return file

    def get_files(self) -> list[FileInfo]:
        """get all files from directory"""
        if not self.service:
            self.start_service()

        results = self.service.files().list(
            q=f"'{self.folder_id}' in parents and trashed = false",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives"
        ).execute()

        files: list[FileInfo] = results.get("files", [])
        return files


def main() -> None:
    """main program"""
    api = ApiWrapper()
    api.auth().start_service()

    # compare files to drive
    local_files = [
        f for f in os.listdir(SOURCE_DIR) if
       os.path.isfile(os.path.join(SOURCE_DIR, f))
    ]
    remote_files = [f["name"] for f in api.get_files()]

    diff = set(local_files) - set(remote_files)

    # move all files that exist in remote to processed dir
    for file in set(local_files) - diff:
        shutil.move(f"{SOURCE_DIR}/{file}", f"{PROCESSED_DIR}/{file}")

    # upload files not present yet and older than 5 minutes
    print("not uploaded: ", diff)

    now = time()
    for file in diff:
        try:
            file_time = float(file.lstrip("gps_debug_").rstrip(".csv"))

        except ValueError:
            print("file name error: ", file)
            shutil.move(f"{SOURCE_DIR}/{file}", f"{PROCESSED_DIR}/{file}")
            continue

        if now - file_time > 60*5:
            # check gps distance > 1km
            with open(f"{SOURCE_DIR}/{file}", "r") as f:
                lines = f.readlines()

                last_line: tuple[float, float] | None = None
                distance = 0
                for line in lines:
                    try:
                        _, m, lat, lon, *_ = line.split(",")

                        if float(m) > 1:
                            if not last_line:
                                last_line: tuple[float, float] = float(lat), float(lon)

                            else:
                                lat, lon = float(lat), float(lon)
                                diff = latlon_to_meters(*last_line, lat, lon)
                                distance += math.sqrt(diff[0] * diff[0] + diff[1] * diff[1])
                                last_line = lat, lon

                    except ValueError:
                        continue

            if distance < 1000:
                print(f"distance to small: {round(distance, 2)} m")
                shutil.move(f"{SOURCE_DIR}/{file}", f"{PROCESSED_DIR}/{file}")
                continue

            print("uploading: ", file, ", time: ", now - file_time, "driven distance: ",
                  round(distance / 1000, 2), " km")
            print(api.upload_file(os.path.join(SOURCE_DIR, file)))

        else:
            print("ignoring: ", file, ", time: ", now-file_time)


if __name__ == "__main__":
    main()
