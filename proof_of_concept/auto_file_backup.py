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

from time import perf_counter
from types import NoneType
import typing as tp
import os

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SOURCE_DIR: str = "/home/nilusink/logs"


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
    local_files = os.listdir(SOURCE_DIR)
    remote_files = [f["name"] for f in api.get_files()]

    diff = set(local_files) - set(remote_files)

    # upload files not present yet and older than 5 minutes
    now = perf_counter()
    for file in diff:
        file_time = float(file.lstrip("gps_debug_").rstrip(".csv"))

        if now - file_time > 60*5:
            print("uploading: ", file, ", time: ", now-file_time)
            print(api.upload_file(os.path.join(SOURCE_DIR, file)))

        else:
            print("ignoring: ", file, ", time: ", now-file_time)


if __name__ == "__main__":
    main()
