import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError


# Define necessary scopes for Google Classroom
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.me',
    'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly',
    'https://www.googleapis.com/auth/classroom.announcements.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly'
]



def authenticate():
    credentials_file_path = './credentials.json'
    token_file_path = './token.json'

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
    credentials = None


    if os.path.exists(token_file_path):
        credentials = Credentials.from_authorized_user_file(token_file_path)

    if not credentials or not credentials.valid:
        credentials = flow.run_local_server(port=0)

        with open(token_file_path, 'w') as token:
            token.write(credentials.to_json())

    return credentials
def download_course_details(classroom_service, course_id, folder_path, credentials):

    announcements = classroom_service.courses().courseWorkMaterials().list(courseId=course_id).execute().get('courseWorkMaterial', [])
    os.makedirs(folder_path, exist_ok=True)
    for announcement in announcements:
        if 'materials' in announcement:
            for material in announcement['materials']:
                if 'driveFile' in material:
                    drive_file_id = material['driveFile']['driveFile']['id']
                    download_drive_file(classroom_service, drive_file_id, folder_path, credentials)

    course_work_items = classroom_service.courses().courseWork().list(courseId=course_id).execute().get('courseWork', [])

    for course_work_item in course_work_items:
        if 'materials' in course_work_item:
            for material in course_work_item['materials']:
                if 'driveFile' in material:
                    drive_file_id = material['driveFile']['driveFile']['id']
                    download_drive_file(classroom_service, drive_file_id, folder_path, credentials)

def download_drive_file(classroom_service, file_id, folder_path, credentials):
    drive_service = build('drive', 'v3', credentials=credentials)
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_metadata = drive_service.files().get(fileId=file_id).execute()

        if 'mimeType' in file_metadata and 'application/vnd.google-apps' in file_metadata['mimeType']:
            request.uri = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=application/pdf"
            file_path = os.path.join(folder_path, f"{file_metadata['name']}.pdf")
        else:
            file_path = os.path.join(folder_path, f"{file_metadata['name']}")


        with open(file_path, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request, chunksize=1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk()
    except HttpError as e:
        if e.resp.status == 404:
            print(f"File not found: {file_id}")
        else:
            print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    credentials = authenticate()

    classroom_service = build('classroom', 'v1', credentials=credentials)

    courses = classroom_service.courses().list().execute().get('courses', [])

    for course in courses:
        course_id = course['id']
        course_name = course['name']
        foldername = course_name.replace(":"," ")
        folder_path = os.path.join('./coursefiles/', f"{foldername}")
        print(f"Downloading course: {course_name} ({course_id})")
        download_course_details(classroom_service, course_id, folder_path, credentials)
        print("Download completed.")
if __name__ == '__main__':
    main()
