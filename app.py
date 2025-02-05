from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from sqlite3 import IntegrityError
from spotifyApi import get_album_info, get_track_info, get_artist_info
import database
import os
import tempfile
import argparse  # Added import for argument parsing

# Configure logging
import logging

logging.basicConfig(level=logging.INFO)

# Secure configuration
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/albums")
def albums():
    albums_list = database.get_albums()
    return render_template("albums.html", albums=albums_list)


@app.route("/tracks")
def tracks():
    tracks_list = database.get_tracks()
    return render_template("tracks.html", tracks=tracks_list)


@app.route("/add_item", methods=["GET", "POST"])
def add_item():
    """Adds an album or track based on the provided Spotify URL."""
    if request.method == "POST":
        spotify_url = request.form["spotify_url"]
        try:
            if "/album/" in spotify_url:
                album_info = get_album_info(spotify_url)
                print(album_info)
                if album_info and "album_id" in album_info:
                    # Ensure artist is inserted
                    artist_info = get_artist_info(album_info["artist_id"])
                    with database.get_connection() as conn:
                        cursor = conn.cursor()
                        database.add_artist(artist_info, cursor)
                        conn.commit()
                    database.add_album(
                        album_info["album_id"],
                        album_info["artist_id"],
                        album_info["album_name"],
                        album_info["release_year"],
                        album_info["album_uri"],
                        spotify_url
                    )
                else:
                    flash("Invalid album information received.", "error")
                    return redirect(url_for("add_item"))
                flash("Album added successfully.", "success")
                return redirect(url_for("albums"))
            elif "/track/" in spotify_url:
                track_info = get_track_info(spotify_url)
                if track_info and "track_id" in track_info:
                    # Ensure artist is inserted
                    artist_info = get_artist_info(track_info["artist_id"])
                    with database.get_connection() as conn:
                        cursor = conn.cursor()
                        database.add_artist(artist_info, cursor)
                        conn.commit()
                    database.add_track(
                        track_info["track_id"],
                        track_info["artist_id"],
                        track_info["album_id"],
                        track_info["track_name"],
                        track_info["release_year"],
                        track_info["track_uri"],
                        spotify_url
                    )
                else:
                    flash("Invalid track information received.", "error")
                    return redirect(url_for("add_item"))
                flash("Track added successfully.", "success")
                return redirect(url_for("tracks"))
            else:
                flash("Invalid Spotify URL. Please provide a valid Album or Track URL.", "error")
                return redirect(url_for("add_item"))
        except IntegrityError:
            flash("Item already exists in the database.", "error")
            return redirect(url_for("add_item"))
        except Exception as e:
            logging.error(f"Error adding item: {e}")
            flash("An error occurred while adding the item.", "error")
            return redirect(url_for("add_item"))
    return render_template("add_item.html")


@app.route("/artists")
def artists():
    """Displays all artists along with their associated genres."""
    artists_list = database.get_artists_with_genres()
    return render_template("artists.html", artists=artists_list)


@app.route("/artist/<artist_id>/albums")
def artist_albums(artist_id):
    try:
        albums_list = database.get_albums_by_artist(artist_id)
        return render_template("artist_albums.html", albums=albums_list)
    except Exception as e:
        flash("Error fetching albums for the artist", "error")
        return redirect(url_for("artists"))


@app.route("/export")
def export_database_route():
    """Exports the database to export.csv and sends it as a downloadable file."""
    database.export_database_csv()
    export_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export.csv")
    return send_file(
        export_file, as_attachment=True, mimetype="text/csv", download_name="export.csv"
    )


@app.route("/import", methods=["GET", "POST"])
def import_database_route():
    """Imports the database from an uploaded CSV file."""
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            filename = secure_filename(file.filename)
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)
            try:
                database.import_database_csv(file_path)
                return redirect(url_for("index"))
            except Exception as e:
                return f"Error importing database: {e}"
        else:
            return "No file provided."
    return render_template("import_database.html")


@app.route("/cleanup", methods=["GET", "POST"])
def cleanup_database_route():
    """Cleans up unused artists and genres with confirmation."""
    if request.method == "POST":
        confirmation = request.form.get("confirmation")
        if confirmation and confirmation.lower() == "yes":
            database.cleanup_unused_artists_and_genres()
            return redirect(url_for("index"))
        else:
            return "Cleanup operation cancelled."
    return render_template("cleanup.html")


@app.route("/delete_album/<album_id>", methods=["POST"])
def delete_album_route(album_id):
    """Deletes an album by its ID."""
    database.delete_album(album_id)
    return redirect(url_for("albums"))


@app.route("/delete_track/<track_id>", methods=["POST"])
def delete_track_route(track_id):
    """Deletes a track by its ID."""
    database.delete_track(track_id)
    return redirect(url_for("tracks"))


@app.route("/genres")
def genres():
    try:
        genres_list = database.list_genres()
        return render_template("genres.html", genres=genres_list)
    except Exception as e:
        flash("Error fetching genres", "error")
        return redirect(url_for("index"))


@app.route("/genres/<int:genre_id>/albums")
def genre_albums(genre_id):
    try:
        albums = database.search_albums_by_genre(genre_id)
        return render_template("genre_albums.html", albums=albums)
    except Exception as e:
        flash("Error fetching albums for the selected genre", "error")
        return redirect(url_for("genres"))


if __name__ == "__main__":
    # Added argument parsing for the database location
    parser = argparse.ArgumentParser(description="Spotify Manager App")
    parser.add_argument(
        "--database", required=True, help="Path to the SQLite database file"
    )
    args = parser.parse_args()

    # Set the database path in the database module (adjust accordingly to your database module usage)
    database.DB_PATH = args.database  # Assumes database module uses this variable

    database.create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)

