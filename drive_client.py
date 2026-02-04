import os
import io

import requests as req
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")

SETUP_INSTRUCTIONS = """
=== Google Cloud Setup (Free, No Billing Required) ===

1. Go to https://console.cloud.google.com/ and sign in.
2. Create a new project (e.g., "georef-map").
3. Go to APIs & Services > Library. Search "Google Drive API" and Enable it.
4. Go to APIs & Services > OAuth consent screen.
   - Select External, click Create.
   - Fill in App name, support email, developer email. Save and Continue.
   - On Scopes: Add "https://www.googleapis.com/auth/drive.readonly". Save.
   - On Test Users: Add your own email. Save.
5. Go to APIs & Services > Credentials. Click Create Credentials > OAuth client ID.
   - Type: Desktop app. Name: anything.
   - Click Create, then Download JSON.
   - Save the file as credentials.json in: {path}
""".strip()


def authenticate():
    """Run OAuth flow if needed, return Credentials object."""
    if not os.path.exists(CREDENTIALS_FILE):
        print()
        print(SETUP_INSTRUCTIONS.format(path=os.path.dirname(CREDENTIALS_FILE) or "."))
        print()
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_FILE}. "
            "Follow the setup instructions above to create it."
        )

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def get_drive_service(creds):
    """Build and return the Drive v3 service object."""
    return build("drive", "v3", credentials=creds)


def find_folder_by_name(service, folder_name):
    """Search for a folder by name. Returns list of {id, name} dicts."""
    safe_name = folder_name.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"mimeType='application/vnd.google-apps.folder' "
        f"and name='{safe_name}' "
        f"and trashed=false"
    )
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=10,
    ).execute()
    return results.get("files", [])


def list_geotagged_images(service, folder_id):
    """
    List all image files in the given folder that have GPS location metadata.
    Returns list of dicts: {id, name, thumbnailLink, lat, lon, altitude}.
    """
    images = []
    page_token = None

    while True:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, thumbnailLink, imageMediaMetadata(location))",
            pageSize=100,
            pageToken=page_token,
        ).execute()

        for f in results.get("files", []):
            meta = f.get("imageMediaMetadata", {})
            location = meta.get("location")
            if location and "latitude" in location and "longitude" in location:
                images.append({
                    "id": f["id"],
                    "name": f["name"],
                    "thumbnailLink": f.get("thumbnailLink"),
                    "lat": location["latitude"],
                    "lon": location["longitude"],
                    "altitude": location.get("altitude"),
                })

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return images


def fetch_thumbnail_bytes(service, file_id, thumbnail_link, creds):
    """
    Fetch thumbnail image bytes for a given file.
    Tries thumbnailLink first (small, fast), falls back to full file download.
    """
    # Ensure token is fresh
    if creds.expired:
        creds.refresh(Request())

    if thumbnail_link:
        headers = {"Authorization": f"Bearer {creds.token}"}
        resp = req.get(thumbnail_link, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.content, resp.headers.get("Content-Type", "image/jpeg")

    # Fallback: download full file via Drive API
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    image_bytes = buffer.read()

    # Try to resize if Pillow is available (drone photos can be 10+ MB)
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((400, 400))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=70)
        return out.getvalue(), "image/jpeg"
    except ImportError:
        return image_bytes, "image/jpeg"
