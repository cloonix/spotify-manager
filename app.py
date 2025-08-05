from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import database
import os
import tempfile

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spotify-manager-secret")

# Spotify API setup
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
))

# Spotify OAuth setup for user authentication
def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:5000/callback"),
        scope="user-follow-read user-library-read"
    )

def get_user_spotify():
    """Get authenticated Spotify client for current user."""
    token_info = session.get('token_info')
    if not token_info:
        return None
    
    spotify_oauth = get_spotify_oauth()
    if spotify_oauth.is_token_expired(token_info):
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    
    return spotipy.Spotify(auth=token_info['access_token'])

def extract_spotify_info(url):
    """Extract info from Spotify URL."""
    try:
        item_id = url.split("/")[-1].split("?")[0]
        
        def build_artist_info(artist_data):
            return {
                "artist_id": artist_data["id"],
                "artist_name": artist_data["name"],
                "genres": artist_data["genres"],
                "uri": artist_data["uri"],
                "external_urls": artist_data["external_urls"]
            }
        
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
                "artist_info": build_artist_info(artist)
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
                "artist_info": build_artist_info(artist)
            }
    except Exception:
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
        export_file = database.export_database_csv()
        return send_file(export_file, as_attachment=True, mimetype="text/csv", download_name="spotify_backup.csv")
    except Exception as e:
        flash(f"Error exporting database: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/import", methods=["GET", "POST"])
def import_database():
    """Import database from CSV file."""
    if request.method == "POST":
        file = request.files.get('file')
        if not file or file.filename == '' or not file.filename.endswith('.csv'):
            flash("Please select a valid CSV file", "error")
            return redirect(url_for("import_database"))
        
        try:
            filename = secure_filename(file.filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)
            
            database.import_database_csv(temp_path)
            os.remove(temp_path)
            
            flash("Database imported successfully!", "success")
            return redirect(url_for("browse"))
        except Exception as e:
            flash(f"Error importing database: {str(e)}", "error")
    
    return render_template("import.html")

@app.route("/download_sqlite")
def download_sqlite():
    """Download SQLite database file."""
    try:
        return send_file(database.DB_PATH, as_attachment=True, mimetype="application/x-sqlite3", download_name="spotify_manager.db")
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

@app.route("/login")
def login():
    """Initiate Spotify OAuth login."""
    spotify_oauth = get_spotify_oauth()
    auth_url = spotify_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    """Handle Spotify OAuth callback."""
    spotify_oauth = get_spotify_oauth()
    code = request.args.get('code')
    
    if code:
        try:
            token_info = spotify_oauth.get_access_token(code)
            session['token_info'] = token_info
            flash("Successfully connected to Spotify!", "success")
        except Exception as e:
            flash(f"Failed to connect to Spotify: {str(e)}", "error")
    else:
        flash("Authorization cancelled", "error")
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    """Logout and clear Spotify session."""
    session.pop('token_info', None)
    flash("Logged out from Spotify", "success")
    return redirect(url_for("index"))

@app.route("/sync-followed-artists", methods=["POST"])
def sync_followed_artists():
    """Sync user's followed artists from Spotify."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        added_count = 0
        results = user_sp.current_user_followed_artists(limit=50)
        
        while results:
            for artist in results['artists']['items']:
                # Build artist info structure
                artist_info = {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"]
                }
                
                # Add to database (will skip if already exists)
                try:
                    database.add_artist(artist_info)
                    added_count += 1
                except Exception:
                    # Artist might already exist, continue
                    pass
            
            # Get next page if available
            if results['artists']['next']:
                results = user_sp.next(results['artists'])
            else:
                break
        
        return jsonify({"success": f"Synced {added_count} followed artists from Spotify"})
    
    except Exception as e:
        return jsonify({"error": f"Error syncing artists: {str(e)}"}), 500

@app.route("/sync-saved-albums", methods=["POST"])
def sync_saved_albums():
    """Sync user's saved albums from Spotify."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        added_count = 0
        results = user_sp.current_user_saved_albums(limit=50)
        
        while results:
            for item in results['items']:
                album = item['album']
                # Get artist details for genres
                artist = sp.artist(album["artists"][0]["id"])
                
                # Build album info structure
                album_info = {
                    "type": "album",
                    "album_id": album["id"],
                    "artist_id": album["artists"][0]["id"],
                    "album_name": album["name"],
                    "artist_name": album["artists"][0]["name"],
                    "release_year": int(album["release_date"].split("-")[0]),
                    "album_uri": album["uri"],
                    "url": album["external_urls"]["spotify"],
                    "artist_info": {
                        "artist_id": artist["id"],
                        "artist_name": artist["name"],
                        "genres": artist["genres"],
                        "uri": artist["uri"],
                        "external_urls": artist["external_urls"]
                    }
                }
                
                try:
                    # Add artist first
                    database.add_artist(album_info["artist_info"])
                    # Add album
                    database.add_album(album_info)
                    added_count += 1
                except Exception:
                    # Album might already exist, continue
                    pass
            
            # Get next page if available
            if results['next']:
                results = user_sp.next(results)
            else:
                break
        
        return jsonify({"success": f"Synced {added_count} saved albums from Spotify"})
    
    except Exception as e:
        return jsonify({"error": f"Error syncing albums: {str(e)}"}), 500

@app.route("/sync-saved-tracks", methods=["POST"])
def sync_saved_tracks():
    """Sync user's saved tracks from Spotify."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        added_count = 0
        results = user_sp.current_user_saved_tracks(limit=50)
        
        while results:
            for item in results['items']:
                track = item['track']
                # Get artist details for genres
                artist = sp.artist(track["artists"][0]["id"])
                
                # Build track info structure
                track_info = {
                    "type": "track",
                    "track_id": track["id"],
                    "artist_id": track["artists"][0]["id"],
                    "album_id": track["album"]["id"],
                    "track_name": track["name"],
                    "artist_name": track["artists"][0]["name"],
                    "release_year": int(track["album"]["release_date"].split("-")[0]),
                    "track_uri": track["uri"],
                    "url": track["external_urls"]["spotify"],
                    "artist_info": {
                        "artist_id": artist["id"],
                        "artist_name": artist["name"],
                        "genres": artist["genres"],
                        "uri": artist["uri"],
                        "external_urls": artist["external_urls"]
                    }
                }
                
                try:
                    # Add artist first
                    database.add_artist(track_info["artist_info"])
                    # Add track
                    database.add_track(track_info)
                    added_count += 1
                except Exception:
                    # Track might already exist, continue
                    pass
            
            # Get next page if available
            if results['next']:
                results = user_sp.next(results)
            else:
                break
        
        return jsonify({"success": f"Synced {added_count} saved tracks from Spotify"})
    
    except Exception as e:
        return jsonify({"error": f"Error syncing tracks: {str(e)}"}), 500

@app.route("/sync-all-spotify", methods=["POST"])
def sync_all_spotify():
    """Sync all user's Spotify data (artists, albums, tracks)."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        total_artists = 0
        total_albums = 0
        total_tracks = 0
        
        # Sync followed artists
        results = user_sp.current_user_followed_artists(limit=50)
        while results:
            for artist in results['artists']['items']:
                artist_info = {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"]
                }
                try:
                    database.add_artist(artist_info)
                    total_artists += 1
                except Exception:
                    pass
            if results['artists']['next']:
                results = user_sp.next(results['artists'])
            else:
                break
        
        # Sync saved albums
        results = user_sp.current_user_saved_albums(limit=50)
        while results:
            for item in results['items']:
                album = item['album']
                artist = sp.artist(album["artists"][0]["id"])
                album_info = {
                    "type": "album",
                    "album_id": album["id"],
                    "artist_id": album["artists"][0]["id"],
                    "album_name": album["name"],
                    "artist_name": album["artists"][0]["name"],
                    "release_year": int(album["release_date"].split("-")[0]),
                    "album_uri": album["uri"],
                    "url": album["external_urls"]["spotify"],
                    "artist_info": {
                        "artist_id": artist["id"],
                        "artist_name": artist["name"],
                        "genres": artist["genres"],
                        "uri": artist["uri"],
                        "external_urls": artist["external_urls"]
                    }
                }
                try:
                    database.add_artist(album_info["artist_info"])
                    database.add_album(album_info)
                    total_albums += 1
                except Exception:
                    pass
            if results['next']:
                results = user_sp.next(results)
            else:
                break
        
        # Sync saved tracks
        results = user_sp.current_user_saved_tracks(limit=50)
        while results:
            for item in results['items']:
                track = item['track']
                artist = sp.artist(track["artists"][0]["id"])
                track_info = {
                    "type": "track",
                    "track_id": track["id"],
                    "artist_id": track["artists"][0]["id"],
                    "album_id": track["album"]["id"],
                    "track_name": track["name"],
                    "artist_name": track["artists"][0]["name"],
                    "release_year": int(track["album"]["release_date"].split("-")[0]),
                    "track_uri": track["uri"],
                    "url": track["external_urls"]["spotify"],
                    "artist_info": {
                        "artist_id": artist["id"],
                        "artist_name": artist["name"],
                        "genres": artist["genres"],
                        "uri": artist["uri"],
                        "external_urls": artist["external_urls"]
                    }
                }
                try:
                    database.add_artist(track_info["artist_info"])
                    database.add_track(track_info)
                    total_tracks += 1
                except Exception:
                    pass
            if results['next']:
                results = user_sp.next(results)
            else:
                break
        
        return jsonify({
            "success": f"Full sync complete! Added {total_artists} artists, {total_albums} albums, {total_tracks} tracks"
        })
    
    except Exception as e:
        return jsonify({"error": f"Error during full sync: {str(e)}"}), 500


if __name__ == "__main__":
    database.DB_PATH = os.environ.get("DATABASE", "spotify_manager.db")
    database.create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)

