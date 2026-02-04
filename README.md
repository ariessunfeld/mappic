# Georef

A local web app that displays geotagged photos from Google Drive on an interactive map — without downloading the images.

Paste a Google Drive folder URL, and Georef plots every geotagged image as a pin on a Leaflet map. Click a pin to see a thumbnail and coordinates. Toggle between street and satellite views. Overlapping pins are automatically clustered.

## Setup

### 1. Google Cloud Project (free, no billing required)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Go to **APIs & Services > Library**, search for **Google Drive API**, and enable it.
3. Go to **APIs & Services > OAuth consent screen**.
   - Select **External**, click Create.
   - Fill in the app name, support email, and developer email. Save and continue.
   - On the **Scopes** page, add `https://www.googleapis.com/auth/drive.readonly`. Save.
   - On the **Test Users** page, add your own email address. Save.
4. Go to **APIs & Services > Credentials**. Click **Create Credentials > OAuth client ID**.
   - Application type: **Desktop app**.
   - Click Create, then **Download JSON**.
   - Save the file as `credentials.json` in this directory.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python app.py
```

On the first run, a browser window opens for Google sign-in. After authorizing, the server starts and you can open [http://localhost:5050](http://localhost:5050).

Subsequent runs use the cached token and skip the sign-in step.

## Usage

1. Open a Google Drive folder containing geotagged photos (e.g., drone images).
2. Copy the folder URL from your browser's address bar.
3. Paste it into the input box on the map page and click **Load**.
4. Pins appear for every image that has GPS metadata. Click a pin to see the photo thumbnail and coordinates.

Use the layer control (top right) to switch between street and satellite map views.

## How it works

- The Google Drive API's `imageMediaMetadata.location` field provides GPS coordinates without downloading images.
- Thumbnails are proxied through the local server (Drive thumbnail URLs require authentication that browsers can't provide directly).
- [Leaflet](https://leafletjs.com/) with [MarkerCluster](https://github.com/Leaflet/Leaflet.markercluster) handles the map rendering.
