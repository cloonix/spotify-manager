import sqlite3
import os
import csv
from spotifyApi import get_artist_info

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Use DB_PATH variable that can be overridden by app.py; default if not provided.
DB_PATH = os.path.join(BASE_DIR, "spotify_manager.db")


def get_connection():
    """Return a new database connection with row factory set."""
    conn = sqlite3.connect(DB_PATH)  # Updated to use DB_PATH
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """
    Creates all necessary tables and indices.
    """
    queries = [
        """CREATE TABLE IF NOT EXISTS Artists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            uri TEXT,
            url TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS Tracks (
            id TEXT PRIMARY KEY,
            artist_id TEXT NOT NULL,
            album_id TEXT NOT NULL,
            name TEXT NOT NULL,
            release_year INTEGER,
            uri TEXT,
            url TEXT,
            FOREIGN KEY (artist_id) REFERENCES Artists(id),
            FOREIGN KEY (album_id) REFERENCES Albums(id)
        )""",
        """CREATE TABLE IF NOT EXISTS Albums (
            id TEXT PRIMARY KEY,
            artist_id TEXT NOT NULL,
            name TEXT NOT NULL,
            release_year INTEGER,
            uri TEXT,
            url TEXT,
            FOREIGN KEY (artist_id) REFERENCES Artists(id)
        )""",
        """CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON Tracks(artist_id)""",
        """CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON Albums(artist_id)""",
        """CREATE TABLE IF NOT EXISTS Genres (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS ArtistGenres (
            artist_id TEXT,
            genre_id INTEGER,
            PRIMARY KEY (artist_id, genre_id),
            FOREIGN KEY (artist_id) REFERENCES Artists(id),
            FOREIGN KEY (genre_id) REFERENCES Genres(id)
        )""",
    ]
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for query in queries:
                cursor.execute(query)
            conn.commit()
    except sqlite3.Error as e:
        raise e


def add_genre(name, artist_id, cursor):
    """
    Adds a genre if it doesn't already exist and links it to the provided artist.
    """
    try:
        cursor.execute("SELECT id FROM Genres WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            genre_id = row[0]
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
    Checks for the artist and inserts it along with its genres if absent.
    """
    try:
        cursor.execute("SELECT id FROM Artists WHERE id = ?", (artist_id,))
        if cursor.fetchone():
            return
        # get_artist_info now returns a dictionary.
        artist_info = get_artist_info(artist_id)
        # Retrieve values from the dictionary
        artist_id = artist_info["artist_id"]
        name = artist_info["artist_name"]
        genres = artist_info["genres"]
        uri = artist_info["uri"]
        external_urls = artist_info["external_urls"]
        cursor.execute(
            "INSERT INTO Artists (id, name, uri, url) VALUES (?, ?, ?, ?)",
            (artist_id, name, uri, external_urls.get("spotify", "")),
        )
        for genre in genres:
            add_genre(genre, artist_id, cursor)
    except sqlite3.Error as e:
        raise e


def add_album(album_id, artist_id, album_name, release_year, uri, url):
    """
    Inserts an album record after ensuring the artist record exists.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            add_artist(artist_id, cursor)
            cursor.execute(
                """INSERT INTO Albums (id, artist_id, name, release_year, uri, url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (album_id, artist_id, album_name, release_year, uri, url),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise e


def add_track(track_id, artist_id, album_id, track_name, release_year, uri, url):
    """
    Inserts a track record after ensuring the artist record exists.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            add_artist(artist_id, cursor)
            cursor.execute(
                """INSERT INTO Tracks (id, artist_id, album_id, name, release_year, uri, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (track_id, artist_id, album_id, track_name, release_year, uri, url),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise e


def delete_album(album_id):
    """
    Deletes an album record based on its ID.
    """
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM Albums WHERE id = ?", (album_id,))
            conn.commit()
    except sqlite3.Error as e:
        raise e


def delete_track(track_id):
    """
    Deletes a track record based on its ID.
    """
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM Tracks WHERE id = ?", (track_id,))
            conn.commit()
    except sqlite3.Error as e:
        raise e


def get_artists():
    """
    Retrieves all artists.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Artists")
            # Return list of dicts instead of raw rows.
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def get_albums():
    """
    Retrieves all albums along with artist name, sorted by artist and release year.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT Albums.id,
                       Artists.id AS artist_id,
                       Artists.name AS artist_name,
                       Albums.name AS album_name,
                       Albums.release_year,
                       Albums.uri,
                       Albums.url
                FROM Albums
                JOIN Artists ON Albums.artist_id = Artists.id
                ORDER BY Artists.name ASC, Albums.release_year ASC
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def get_genres():
    """
    Retrieves all genres.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Genres")
            return cursor.fetchall()
    except sqlite3.Error as e:
        raise e


def get_tracks():
    """
    Retrieves all tracks with artist and album info, sorted by artist and track name.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT Tracks.id, Artists.name AS artist_name, Albums.name AS album_name,
                       Tracks.name AS track_name, Tracks.release_year, Tracks.uri, Tracks.url
                FROM Tracks
                LEFT JOIN Artists ON Tracks.artist_id = Artists.id
                LEFT JOIN Albums ON Tracks.album_id = Albums.id
                ORDER BY Artists.name ASC, Tracks.name ASC
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def get_artists_with_genres():
    """
    Retrieves all artists along with a comma-separated list of genres.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT Artists.id, Artists.name AS artist_name,
                       GROUP_CONCAT(Genres.name, ', ') as genres, Artists.uri
                FROM Artists
                LEFT JOIN ArtistGenres ON Artists.id = ArtistGenres.artist_id
                LEFT JOIN Genres ON ArtistGenres.genre_id = Genres.id
                GROUP BY Artists.id
            """
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def export_database_csv():
    """
    Exports all database tables to a CSV file.
    """
    tables = {
        "artists": ["id", "name", "uri", "url"],
        "albums": ["id", "artist_id", "name", "release_year", "uri", "url"],
        "tracks": ["id", "artist_id", "album_id", "name", "release_year", "uri", "url"],
        "genres": ["id", "name"],
        "artistgenres": ["artist_id", "genre_id"],
    }
    try:
        export_file = os.path.join(BASE_DIR, "export.csv")
        with open(export_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            for table, columns in tables.items():
                writer.writerow([f"[{table}]"])
                writer.writerow(columns)
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT {', '.join(columns)} FROM {table}")
                    writer.writerows(cursor.fetchall())
                writer.writerow([])  # Blank line between tables
        print("Database exported successfully to export.csv.")
    except Exception as e:
        print(f"Error exporting database: {e}")


def import_database_csv(import_file=None):
    """
    Imports database data from a CSV file, overwriting existing data.
    """
    try:
        if not import_file:
            import_file = os.path.join(BASE_DIR, "export.csv")
        if not os.path.exists(import_file):
            print(f"{import_file} does not exist.")
            return
        with open(import_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            current_table = None
            headers = []
            data = []
            for row in reader:
                if not row:
                    continue
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
        print(f"Database imported successfully from {import_file}.")
    except Exception as e:
        print(f"Error importing database: {e}")


def _insert_data(table, columns, data):
    """
    Helper function to insert data into specified table.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table}")
            placeholders = ",".join(["?"] * len(columns))
            cursor.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                data,
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data into {table}: {e}")


def cleanup_unused_artists_and_genres():
    """
    Deletes artists not linked to any tracks or albums and removes orphan genres.
    """
    try:
        with get_connection() as conn:
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
            print("Cleanup completed successfully.")
    except sqlite3.Error as e:
        print(f"Error during cleanup: {e}")


def search_albums_by_genre(genre_id):
    """
    Retrieves albums associated with a specific genre.
    Returns album details along with the artist name.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT Albums.id, Albums.artist_id, Artists.name AS artist_name,
                       Albums.name AS album_name, Albums.release_year, Albums.uri, Albums.url
                FROM Albums
                JOIN Artists ON Albums.artist_id = Artists.id
                JOIN ArtistGenres ON Artists.id = ArtistGenres.artist_id
                JOIN Genres ON ArtistGenres.genre_id = Genres.id
                WHERE Genres.id = ?
                ORDER BY Albums.release_year ASC
            """
            cursor.execute(query, (genre_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def list_genres():
    """
    Retrieves all genres with their ID and name.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM Genres ORDER BY name ASC")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e


def get_albums_by_artist(artist_id):
    """
    Retrieves all albums by a specific artist.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT Albums.id, Artists.name AS artist_name, Albums.name AS album_name,
                       Albums.release_year, Albums.uri, Albums.url
                FROM Albums
                JOIN Artists ON Albums.artist_id = Artists.id
                WHERE Artists.id = ?
                ORDER BY Albums.release_year ASC
            """
            cursor.execute(query, (artist_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise e
