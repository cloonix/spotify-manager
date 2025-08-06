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
        scope="user-follow-read user-library-read user-follow-modify user-library-modify"
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
                "external_urls": artist_data["external_urls"],
                "images": artist_data.get("images", [])
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
    search_query = request.args.get("search", "")
    artist_query = request.args.get("artist", "")
    
    # If artist parameter is provided, use it as the search query
    if artist_query:
        search_query = artist_query
    
    items = database.get_all_items()
    
    if filter_type != "all":
        items = [item for item in items if item["type"] == filter_type]
    
    return render_template("browse.html", items=items, filter_type=filter_type, search_query=search_query)

@app.route("/artists")
def artists():
    artists_list = database.get_artists()
    return render_template("artists.html", artists=artists_list)

@app.route("/add", methods=["POST"])
def add_item():
    """Add item via AJAX and save to Spotify library."""
    url = request.form.get("spotify_url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    info = extract_spotify_info(url)
    if not info:
        return jsonify({"error": "Invalid Spotify URL or API error"}), 400
    
    try:
        # Add artist first
        database.add_artist(info["artist_info"])
        
        # Add to local database
        if info["type"] == "album":
            database.add_album(info)
            item_name = f"Album '{info['album_name']}'"
        else:
            database.add_track(info)
            item_name = f"Track '{info['track_name']}'"
        
        # Also save to user's Spotify library
        user_sp = get_user_spotify()
        spotify_saved = False
        
        if user_sp:
            try:
                if info["type"] == "album":
                    user_sp.current_user_saved_albums_add([info["album_id"]])
                    spotify_saved = True
                else:
                    user_sp.current_user_saved_tracks_add([info["track_id"]])
                    spotify_saved = True
            except Exception as e:
                # Continue even if Spotify save fails
                print(f"Failed to save to Spotify: {e}")
        
        # Provide appropriate feedback
        if spotify_saved:
            message = f"{item_name} added successfully and saved to your Spotify library"
        else:
            message = f"{item_name} added to local database (Spotify save failed - please ensure you're logged in)"
        
        return jsonify({"success": message})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/delete/<item_type>/<item_id>", methods=["POST"])
def delete_item(item_type, item_id):
    """Delete item locally and remove from Spotify to maintain sync."""
    try:
        # Get item name for better messaging
        item_name = "Unknown"
        if item_type == 'album':
            album = database.get_album_by_id(item_id)
            if album:
                item_name = f"{album['name']} by {album['artist_name']}"
        
        # Try to remove from Spotify first to maintain sync
        user_sp = get_user_spotify()
        spotify_removed = False
        
        if user_sp:
            try:
                if item_type == 'album':
                    user_sp.current_user_saved_albums_delete([item_id])
                    spotify_removed = True
                elif item_type == 'track':
                    user_sp.current_user_saved_tracks_delete([item_id])
                    spotify_removed = True
            except Exception:
                # Continue with local deletion even if Spotify fails
                pass
        
        # Always delete locally
        database.delete_item(item_id, item_type)
        
        # Provide appropriate feedback
        if spotify_removed:
            return jsonify({"success": f"{item_type.title()} '{item_name}' removed from both local database and Spotify library"})
        else:
            return jsonify({"success": f"{item_type.title()} '{item_name}' deleted locally", "warning": "Could not remove from Spotify - please sync to maintain consistency"})
            
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
    """Sync user's followed artists from Spotify with proper bi-directional sync."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        # Get all currently followed artists from Spotify
        spotify_artist_ids = set()
        results = user_sp.current_user_followed_artists(limit=50)
        
        # Collect all followed artist IDs from Spotify
        while results:
            for artist in results['artists']['items']:
                spotify_artist_ids.add(artist["id"])
                
                # Build artist info structure
                artist_info = {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"],
                    "images": artist.get("images", [])
                }
                
                # Add/update artist in database
                try:
                    database.add_artist(artist_info)
                except Exception:
                    pass  # Continue if there's an issue with this artist
            
            # Get next page if available
            if results['artists']['next']:
                results = user_sp.next(results['artists'])
            else:
                break
        
        # Get all artists currently in local database
        local_artists = database.get_artists()
        local_artist_ids = {artist['id'] for artist in local_artists}
        
        # Find artists that are in local database but not followed on Spotify anymore
        unfollowed_artist_ids = local_artist_ids - spotify_artist_ids
        
        # Remove unfollowed artists, but only if they're not linked to any tracks/albums
        removed_count = 0
        for artist_id in unfollowed_artist_ids:
            # Check if artist has any tracks or albums in the database
            if not database.artist_has_content(artist_id):
                try:
                    database.delete_artist(artist_id)
                    removed_count += 1
                except Exception:
                    pass  # Continue if there's an issue removing this artist
        
        added_count = len(spotify_artist_ids - local_artist_ids)
        
        # Build response message
        message_parts = []
        if added_count > 0:
            message_parts.append(f"Added {added_count} new artists")
        if removed_count > 0:
            message_parts.append(f"removed {removed_count} unfollowed artists")
        
        if message_parts:
            message = "Sync complete: " + " and ".join(message_parts)
        else:
            message = "Artists already in sync - no changes needed"
            
        return jsonify({"success": message})
    
    except Exception as e:
        return jsonify({"error": f"Error syncing artists: {str(e)}"}), 500

@app.route("/sync-saved-albums", methods=["POST"])
def sync_saved_albums():
    """Sync user's saved albums from Spotify with proper bi-directional sync."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        # Get all currently saved albums from Spotify
        spotify_album_ids = set()
        results = user_sp.current_user_saved_albums(limit=50)
        
        # Collect all saved album IDs from Spotify
        while results:
            for item in results['items']:
                album = item['album']
                album_id = album["id"]
                spotify_album_ids.add(album_id)
                
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
                        "external_urls": artist["external_urls"],
                        "images": artist.get("images", [])
                    }
                }
                
                try:
                    # Add artist first
                    database.add_artist(album_info["artist_info"])
                    # Add album
                    database.add_album(album_info)
                except Exception:
                    pass  # Continue if there's an issue with this album
            
            # Get next page if available
            if results['next']:
                results = user_sp.next(results)
            else:
                break
        
        # Get all albums currently in local database
        local_albums = database.get_albums()
        local_album_ids = {album['id'] for album in local_albums}
        
        # Find albums that are in local database but not saved on Spotify anymore
        unsaved_album_ids = local_album_ids - spotify_album_ids
        
        # Remove unsaved albums, but only if they don't have any tracks in database
        removed_count = 0
        for album_id in unsaved_album_ids:
            # Check if album has any tracks in the database
            if not database.album_has_tracks(album_id):
                try:
                    database.delete_album(album_id)
                    removed_count += 1
                except Exception:
                    pass  # Continue if there's an issue removing this album
        
        added_count = len(spotify_album_ids - local_album_ids)
        
        # Build response message
        message_parts = []
        if added_count > 0:
            message_parts.append(f"Added {added_count} new albums")
        if removed_count > 0:
            message_parts.append(f"removed {removed_count} unsaved albums")
        
        if message_parts:
            message = "Sync complete: " + " and ".join(message_parts)
        else:
            message = "Albums already in sync - no changes needed"
        
        return jsonify({"success": message})
    
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
                        "external_urls": artist["external_urls"],
                        "images": artist.get("images", [])
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
        
        # Sync followed artists with bi-directional sync
        spotify_artist_ids = set()
        results = user_sp.current_user_followed_artists(limit=50)
        while results:
            for artist in results['artists']['items']:
                spotify_artist_ids.add(artist["id"])
                artist_info = {
                    "artist_id": artist["id"],
                    "artist_name": artist["name"],
                    "genres": artist["genres"],
                    "uri": artist["uri"],
                    "external_urls": artist["external_urls"],
                    "images": artist.get("images", [])
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
        
        # Remove unfollowed artists (only if they have no tracks/albums)
        local_artists = database.get_artists()
        local_artist_ids = {artist['id'] for artist in local_artists}
        unfollowed_artist_ids = local_artist_ids - spotify_artist_ids
        
        removed_artists = 0
        for artist_id in unfollowed_artist_ids:
            if not database.artist_has_content(artist_id):
                try:
                    database.delete_artist(artist_id)
                    removed_artists += 1
                except Exception:
                    pass
        
        # Sync saved albums with bi-directional sync
        spotify_album_ids = set()
        results = user_sp.current_user_saved_albums(limit=50)
        while results:
            for item in results['items']:
                album = item['album']
                album_id = album["id"]
                spotify_album_ids.add(album_id)
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
                        "external_urls": artist["external_urls"],
                        "images": artist.get("images", [])
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
        
        # Remove unsaved albums (only if they have no tracks)
        local_albums = database.get_albums()
        local_album_ids = {album['id'] for album in local_albums}
        unsaved_album_ids = local_album_ids - spotify_album_ids
        
        removed_albums = 0
        for album_id in unsaved_album_ids:
            if not database.album_has_tracks(album_id):
                try:
                    database.delete_album(album_id)
                    removed_albums += 1
                except Exception:
                    pass
        
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
                        "external_urls": artist["external_urls"],
                        "images": artist.get("images", [])
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
        
        message_parts = [f"Added {total_artists} artists", f"{total_albums} albums", f"{total_tracks} tracks"]
        if removed_artists > 0:
            message_parts.append(f"removed {removed_artists} unfollowed artists")
        if removed_albums > 0:
            message_parts.append(f"removed {removed_albums} unsaved albums")
        
        return jsonify({
            "success": f"Full sync complete! {', '.join(message_parts)}"
        })
    
    except Exception as e:
        return jsonify({"error": f"Error during full sync: {str(e)}"}), 500

@app.route("/unfollow-artist/<artist_id>", methods=["POST"])
def unfollow_artist(artist_id):
    """Unfollow an artist on Spotify."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        # Get artist name for response message
        artist = database.get_artist_by_id(artist_id)
        artist_name = artist['name'] if artist else "Unknown Artist"
        
        # Unfollow on Spotify
        user_sp.user_unfollow_artists([artist_id])
        
        return jsonify({"success": f"Successfully unfollowed {artist_name} on Spotify"})
    
    except Exception as e:
        return jsonify({"error": f"Error unfollowing artist: {str(e)}"}), 500

@app.route("/unsave-album/<album_id>", methods=["POST"])
def unsave_album(album_id):
    """Unsave an album on Spotify."""
    user_sp = get_user_spotify()
    if not user_sp:
        return jsonify({"error": "Please login with Spotify first"}), 401
    
    try:
        # Get album name for response message
        album = database.get_album_by_id(album_id)
        album_name = f"{album['name']} by {album['artist_name']}" if album else "Unknown Album"
        
        # Unsave on Spotify
        user_sp.current_user_saved_albums_delete([album_id])
        
        return jsonify({"success": f"Successfully removed {album_name} from saved albums"})
    
    except Exception as e:
        return jsonify({"error": f"Error unsaving album: {str(e)}"}), 500

@app.route("/artist-details/<artist_id>")
def get_artist_details(artist_id):
    """Get detailed artist information."""
    try:
        # Get artist from database
        artist = database.get_artist_by_id(artist_id)
        if not artist:
            return jsonify({"error": "Artist not found"}), 404
        
        # Get fresh data from Spotify API for more details
        fresh_artist = sp.artist(artist_id)
        
        # Get user's follow status if logged in
        user_sp = get_user_spotify()
        is_following = False
        if user_sp:
            try:
                following_result = user_sp.current_user_following_artists([artist_id])
                is_following = following_result[0] if following_result else False
            except:
                pass  # Not critical if this fails
        
        return jsonify({
            "id": artist['id'],
            "name": artist['name'],
            "genres": artist['genres'],
            "image_url": artist.get('image_url', ''),
            "spotify_url": artist['url'],
            "followers": fresh_artist.get('followers', {}).get('total', 0),
            "popularity": fresh_artist.get('popularity', 0),
            "is_following": is_following
        })
    
    except Exception as e:
        return jsonify({"error": f"Error getting artist details: {str(e)}"}), 500

@app.route("/album-details/<album_id>")
def get_album_details(album_id):
    """Get detailed album information."""
    try:
        # Get album from database
        album = database.get_album_by_id(album_id)
        if not album:
            return jsonify({"error": "Album not found"}), 404
        
        # Get fresh data from Spotify API for more details
        fresh_album = sp.album(album_id)
        
        # Get user's saved status if logged in
        user_sp = get_user_spotify()
        is_saved = False
        if user_sp:
            try:
                saved_result = user_sp.current_user_saved_albums_contains([album_id])
                is_saved = saved_result[0] if saved_result else False
            except:
                pass  # Not critical if this fails
        
        return jsonify({
            "id": album['id'],
            "name": album['name'],
            "artist_name": album['artist_name'],
            "artist_id": album['artist_id'],
            "release_year": album['release_year'],
            "spotify_url": album['url'],
            "image_url": fresh_album.get('images', [{}])[0].get('url', '') if fresh_album.get('images') else '',
            "total_tracks": fresh_album.get('total_tracks', 0),
            "popularity": fresh_album.get('popularity', 0),
            "is_saved": is_saved
        })
    
    except Exception as e:
        return jsonify({"error": f"Error getting album details: {str(e)}"}), 500


if __name__ == "__main__":
    database.DB_PATH = os.environ.get("DATABASE", "spotify_manager.db")
    database.create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)

