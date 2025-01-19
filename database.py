import sqlite3
import os
from spotifyApi import get_artist_info
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, "spotify_manager.db")


def create_tables():
    """
    Creates necessary tables in the database and adds initial indices.
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Artists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    uri TEXT,
                    url TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Tracks (
                    id TEXT PRIMARY KEY,
                    artist_id TEXT NOT NULL,
                    album_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    release_year INTEGER,
                    uri TEXT,
                    url TEXT,
                    FOREIGN KEY (artist_id) REFERENCES Artists(id),
                    FOREIGN KEY (album_id) REFERENCES Albums(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Albums (
                    id TEXT PRIMARY KEY,
                    artist_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    release_year INTEGER,
                    uri TEXT,
                    url TEXT,
                    FOREIGN KEY (artist_id) REFERENCES Artists(id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tracks_artist_id
                ON Tracks(artist_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_albums_artist_id
                ON Albums(artist_id)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Genres (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ArtistGenres (
                    artist_id TEXT,
                    genre_id INTEGER,
                    PRIMARY KEY (artist_id, genre_id),
                    FOREIGN KEY (artist_id) REFERENCES Artists(id),
                    FOREIGN KEY (genre_id) REFERENCES Genres(id)
                )
            """)
    except sqlite3.Error as e:
        raise e


def add_genre(name, artist_id, cursor):
    """
    Adds a new genre to the Genres table if it doesn't exist, associates it with the artist, and returns its ID.
    :param name: Name of the genre to add
    :param artist_id: ID of the artist to associate with the genre
    :param cursor: SQLite database cursor
    :return: ID of the genre
    """
    try:
        cursor.execute("SELECT id FROM Genres WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result:
            genre_id = result[0]
        else:
            cursor.execute("INSERT INTO Genres (name) VALUES (?)", (name,))
            genre_id = cursor.lastrowid
        cursor.execute(
            "INSERT OR IGNORE INTO ArtistGenres (artist_id, genre_id) VALUES (?, ?)",
            (artist_id, genre_id),
        )
        return genre_id
    except sqlite3.Error as e:
        raise e


def add_artist(artist_id, cursor):
    """
    Adds a new artist to the Artists table and associates genres.
    If the artist already exists, the function returns immediately.
    :param artist_id: ID of the artist to add
    :param cursor: SQLite database cursor
    """
    try:
        cursor.execute("SELECT id FROM Artists WHERE id = ?", (artist_id,))
        if cursor.fetchone():
            return

        artist_id, name, genres, uri, external_urls = get_artist_info(artist_id)

        cursor.execute(
            "INSERT INTO Artists (id, name, uri, url) VALUES (?, ?, ?, ?)",
            (artist_id, name, uri, external_urls["spotify"]),
        )

        for genre in genres:
            add_genre(genre, artist_id, cursor)
    except sqlite3.Error as e:
        raise e


def add_album(album_id, artist_id, album_name, release_year, uri, url):
    """
    Adds a new album to the 'Albums' table, creating the artist and assigning genres if needed.
    :param album_id: Unique album ID
    :param artist_id: Unique artist ID
    :param artist_name: Name of the artist
    :param album_name: Name of the album
    :param release_year: Release year of the album
    :param uri: URI link for the album
    :param url: URL link for the album
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            add_artist(artist_id, cursor)

            cursor.execute(
                """
                INSERT INTO Albums (id, artist_id, name, release_year, uri, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (album_id, artist_id, album_name, release_year, uri, url),
            )

    except sqlite3.Error as e:
        raise e


def add_track(track_id, artist_id, album_id, track_name, release_year, uri, url):
    """
    Adds a new track to the 'Tracks' table, creating the artist and album if needed.
    :param track_id: Unique track ID
    :param artist_id: Unique artist ID
    :param album_id: Unique album ID
    :param track_name: Name of the track
    :param release_year: Release year of the track
    :param uri: URI link for the track
    :param url: URL link for the track
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            add_artist(artist_id, cursor)

            cursor.execute(
                """
                INSERT INTO Tracks (id, artist_id, album_id, name, release_year, uri, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (track_id, artist_id, album_id, track_name, release_year, uri, url),
            )
    except sqlite3.Error as e:
        raise e


def delete_album(album_id):
    """
    Deletes an album from the Albums table.
    :param album_id: ID of the album to delete
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Albums WHERE id = ?", (album_id,))
    except sqlite3.Error as e:
        raise e


def delete_track(track_id):
    """
    Deletes a track from the Track stable.
    :param track_id: ID of the track to delete
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Tracks WHERE id = ?", (track_id,))
    except sqlite3.Error as e:
        raise e


def get_artists():
    """
    Retrieves all artists from the Artists table.
    :return: List of artists
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Artists")
            artists = cursor.fetchall()
            return artists
    except sqlite3.Error as e:
        raise e


def get_albums():
    """
    Retrieves all albums from the Albums table, sorted by artist name and album release year.
    :return: List of albums
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Albums.id, Artists.name, Albums.name, Albums.release_year, Albums.uri, Albums.url
                FROM Albums
                JOIN Artists ON Albums.artist_id = Artists.id
                ORDER BY Artists.name ASC, Albums.release_year ASC
            """)
            albums = cursor.fetchall()
            return albums
    except sqlite3.Error as e:
        raise e


def get_genres():
    """
    Retrieves all genres from the Genres table.
    :return: List of genres
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Genres")
            genres = cursor.fetchall()
            return genres
    except sqlite3.Error as e:
        raise e


def get_tracks():
    """
    Retrieves all tracks from the Tracks table, sorted by artist name and track name.
    :return: List of tracks
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Tracks.id, Artists.name, Albums.name, Tracks.name, Tracks.release_year, Tracks.uri, Tracks.url
                FROM Tracks
                LEFT JOIN Artists ON Tracks.artist_id = Artists.id
                LEFT JOIN Albums ON Tracks.album_id = Albums.id
                ORDER BY Artists.name ASC, Tracks.name ASC
            """)
            tracks = cursor.fetchall()
            return tracks
    except sqlite3.Error as e:
        raise e


def get_artists_with_genres():
    """
    Retrieves all artists along with their associated genres.
    :return: List of tuples containing artist name and their genres
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Artists.name, GROUP_CONCAT(Genres.name, ', ') as genres, Artists.uri
                FROM Artists
                LEFT JOIN ArtistGenres ON Artists.id = ArtistGenres.artist_id
                LEFT JOIN Genres ON ArtistGenres.genre_id = Genres.id
                GROUP BY Artists.id
            """)
            artists = cursor.fetchall()
            return artists
    except sqlite3.Error as e:
        raise e


def export_database_csv():
    """Exports the database tables to a single export.csv file in the local directory."""
    try:
        export_file = os.path.join(BASE_DIR, "export.csv")
        with open(export_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            tables = {
                "artists": ["id", "name", "uri", "url"],
                "albums": ["id", "artist_id", "name", "release_year", "uri", "url"],
                "tracks": [
                    "id",
                    "artist_id",
                    "album_id",
                    "name",
                    "release_year",
                    "uri",
                    "url",
                ],
                "genres": ["id", "name"],
                "artistgenres": ["artist_id", "genre_id"],
            }

            for table, columns in tables.items():
                writer.writerow([f"[{table}]"])
                writer.writerow(columns)
                with sqlite3.connect(DATABASE_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT {', '.join(columns)} FROM {table}")
                    rows = cursor.fetchall()
                    writer.writerows(rows)
                writer.writerow([])  # Add an empty line between tables
        print("Database exported successfully to export.csv.\n")
    except Exception as e:
        print(f"Error exporting database: {e}\n")


def import_database_csv(import_file=None):
    """Imports the database tables from the provided CSV file, overwriting existing data."""
    try:
        if not import_file:
            import_file = os.path.join(BASE_DIR, "export.csv")
        if not os.path.exists(import_file):
            print(f"{import_file} does not exist.\n")
            return

        with open(import_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            current_table = None
            headers = []
            data = []
            for row in reader:
                if not row:
                    continue  # Skip empty lines
                if row[0].startswith("[") and row[0].endswith("]"):
                    if current_table and data:
                        _insert_data(current_table, headers, data)
                        data = []
                    current_table = row[0][1:-1]
                    headers = []
                elif not headers:
                    headers = row
                else:
                    data.append(row)
            if current_table and data:
                _insert_data(current_table, headers, data)

        print(f"Database imported successfully from {import_file}.\n")
    except Exception as e:
        print(f"Error importing database: {e}\n")


def _insert_data(table, columns, data):
    """Helper function to insert data into the specified table."""
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table}")
            placeholders = ",".join(["?"] * len(columns))
            cursor.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                data,
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data into {table}: {e}\n")


def cleanup_unused_artists_and_genres():
    """
    Deletes artists not associated with any tracks or albums and genres not associated with any artists.
    """
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM Artists
                WHERE id NOT IN (
                    SELECT DISTINCT artist_id FROM Tracks
                    UNION
                    SELECT DISTINCT artist_id FROM Albums
                )
            """)

            cursor.execute("""
                DELETE FROM ArtistGenres 
                WHERE artist_id NOT IN (
                    SELECT DISTINCT artist_id FROM Artists
                )
            """)

            cursor.execute("""
                DELETE FROM Genres
                WHERE id NOT IN (
                    SELECT DISTINCT genre_id FROM ArtistGenres
                )
            """)

            conn.commit()
            print("Cleanup completed successfully.\n")
    except sqlite3.Error as e:
        print(f"Error during cleanup: {e}\n")
