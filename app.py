from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from sqlite3 import IntegrityError
from spotifyApi import get_album_info, get_track_info
import database
import os
import tempfile

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
                if len(album_info) == 5:
                    database.add_album(*album_info, spotify_url)
                else:
                    flash("Invalid album information received.", "error")
                    return redirect(url_for("add_item"))
                flash("Album added successfully.", "success")
                return redirect(url_for("albums"))

            elif "/track/" in spotify_url:
                track_info = get_track_info(spotify_url)
                if len(track_info) == 6:
                    database.add_track(*track_info, spotify_url)
                else:
                    flash("Invalid track information received.", "error")
                    return redirect(url_for("add_item"))
                flash("Track added successfully.", "success")
                return redirect(url_for("tracks"))
            else:
                flash(
                    "Invalid Spotify URL. Please provide a valid Album or Track URL.",
                    "error",
                )
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


if __name__ == "__main__":
    database.create_tables()
    app.run(debug=True)
