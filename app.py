from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import database
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spotify-manager-secret")

# Spotify API setup
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
))

def extract_spotify_info(url):
    """Extract info from Spotify URL."""
    try:
        item_id = url.split("/")[-1].split("?")[0]
        
        if "/album/" in url:
            album = sp.album(item_id)
            artist = sp.artist(album["artists"][0]["id"])
            return {
                "type": "album",
                "album_id": album["id"],
                "artist_id": album["artists"][0]["id"],
                "album_name": album["name"],
                "artist_name": album["artists"][0]["name"],
                "release_year": int(album["release_date"].split("-")[0]),
                "album_uri": album["uri"],
                "url": url,
                "artist_info": {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"]
                }
            }
        elif "/track/" in url:
            track = sp.track(item_id)
            artist = sp.artist(track["artists"][0]["id"])
            return {
                "type": "track",
                "track_id": track["id"],
                "artist_id": track["artists"][0]["id"],
                "album_id": track["album"]["id"],
                "track_name": track["name"],
                "artist_name": track["artists"][0]["name"],
                "release_year": int(track["album"]["release_date"].split("-")[0]),
                "track_uri": track["uri"],
                "url": url,
                "artist_info": {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"]
                }
            }
    except Exception as e:
        return None


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/browse")
def browse():
    """Browse all items with optional filtering."""
    filter_type = request.args.get("type", "all")
    items = database.get_all_items()
    
    if filter_type != "all":
        items = [item for item in items if item["type"] == filter_type]
    
    return render_template("browse.html", items=items, filter_type=filter_type)

@app.route("/artists")
def artists():
    artists_list = database.get_artists()
    return render_template("artists.html", artists=artists_list)

@app.route("/add", methods=["POST"])
def add_item():
    """Add item via AJAX."""
    url = request.form.get("spotify_url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    info = extract_spotify_info(url)
    if not info:
        return jsonify({"error": "Invalid Spotify URL or API error"}), 400
    
    try:
        # Add artist first
        database.add_artist(info["artist_info"])
        
        # Add album or track
        if info["type"] == "album":
            database.add_album(info)
            message = f"Album '{info['album_name']}' added successfully"
        else:
            database.add_track(info)
            message = f"Track '{info['track_name']}' added successfully"
        
        return jsonify({"success": message})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/delete/<item_type>/<item_id>", methods=["POST"])
def delete_item(item_type, item_id):
    """Delete item via AJAX."""
    try:
        database.delete_item(item_id, item_type)
        return jsonify({"success": f"{item_type.title()} deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Error deleting {item_type}: {str(e)}"}), 500

@app.route("/export")
def export_database():
    """Export database to CSV file."""
    try:
        from flask import send_file
        export_file = database.export_database_csv()
        return send_file(
            export_file, 
            as_attachment=True, 
            mimetype="text/csv", 
            download_name="spotify_backup.csv"
        )
    except Exception as e:
        flash(f"Error exporting database: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/import", methods=["GET", "POST"])
def import_database():
    """Import database from CSV file."""
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No file selected", "error")
            return redirect(url_for("import_database"))
        
        file = request.files['file']
        if file.filename == '':
            flash("No file selected", "error")
            return redirect(url_for("import_database"))
        
        if file and file.filename.endswith('.csv'):
            try:
                import tempfile
                import os
                from werkzeug.utils import secure_filename
                
                filename = secure_filename(file.filename)
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                file.save(temp_path)
                
                database.import_database_csv(temp_path)
                os.remove(temp_path)
                
                flash("Database imported successfully!", "success")
                return redirect(url_for("browse"))
            except Exception as e:
                flash(f"Error importing database: {str(e)}", "error")
        else:
            flash("Please select a valid CSV file", "error")
    
    return render_template("import.html")

@app.route("/download_sqlite")
def download_sqlite():
    """Download SQLite database file."""
    try:
        from flask import send_file
        return send_file(
            database.DB_PATH,
            as_attachment=True,
            mimetype="application/x-sqlite3",
            download_name="spotify_manager.db"
        )
    except Exception as e:
        flash(f"Error downloading database: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/cleanup", methods=["POST"])
def cleanup():
    """Clean up unused artists."""
    try:
        removed_count = database.cleanup_unused_artists()
        return jsonify({"success": f"Removed {removed_count} unused artists"})
    except Exception as e:
        return jsonify({"error": f"Error during cleanup: {str(e)}"}), 500


if __name__ == "__main__":
    database.DB_PATH = os.environ.get("DATABASE", "spotify_manager.db")
    database.create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)

