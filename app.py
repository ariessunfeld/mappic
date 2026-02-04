import sys
from flask import Flask, render_template, request, jsonify, Response
from drive_client import (
    authenticate,
    get_drive_service,
    find_folder_by_name,
    list_geotagged_images,
    fetch_thumbnail_bytes,
)

app = Flask(__name__)

# Module-level state (single-user local app)
creds = None
service = None
# Cache thumbnailLinks from image listing to avoid extra API calls
thumbnail_link_cache = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/folders")
def api_folders():
    """Search Drive for folders matching a name."""
    folder_name = request.args.get("name", "").strip()
    if not folder_name:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    folders = find_folder_by_name(service, folder_name)
    if not folders:
        return jsonify({"error": f"No folder found with name '{folder_name}'"}), 404

    return jsonify({"folders": folders})


@app.route("/api/images")
def api_images():
    """List all geotagged images in a Drive folder."""
    folder_id = request.args.get("folder_id", "").strip()
    if not folder_id:
        return jsonify({"error": "Missing 'folder_id' parameter"}), 400

    images = list_geotagged_images(service, folder_id)

    # Cache thumbnailLinks for the proxy endpoint
    for img in images:
        if img.get("thumbnailLink"):
            thumbnail_link_cache[img["id"]] = img["thumbnailLink"]

    return jsonify({
        "images": images,
        "count": len(images),
    })


@app.route("/api/thumbnail/<file_id>")
def api_thumbnail(file_id):
    """Proxy a thumbnail from Google Drive."""
    thumbnail_link = thumbnail_link_cache.get(file_id)

    if not thumbnail_link:
        # Fetch it from the API if not cached
        try:
            file_meta = service.files().get(
                fileId=file_id, fields="thumbnailLink"
            ).execute()
            thumbnail_link = file_meta.get("thumbnailLink")
        except Exception:
            pass

    image_bytes, content_type = fetch_thumbnail_bytes(
        service, file_id, thumbnail_link, creds
    )

    return Response(
        image_bytes,
        mimetype=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


if __name__ == "__main__":
    print("Authenticating with Google Drive...")
    try:
        creds = authenticate()
        service = get_drive_service(creds)
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)

    print("Authentication successful.")
    print("Starting map server at http://localhost:5050")
    print("Open that URL in your browser, then enter a Google Drive folder name.")
    app.run(host="127.0.0.1", port=5050, debug=False)
