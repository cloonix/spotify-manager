import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "spotify_manager.db")

def get_connection():
    """Return a new database connection with row factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Creates simplified database schema."""
    with get_connection() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS Artists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                genres TEXT,
                uri TEXT,
                url TEXT,
                image_url TEXT
            );
            
            CREATE TABLE IF NOT EXISTS Albums (
                id TEXT PRIMARY KEY,
                artist_id TEXT NOT NULL,
                name TEXT NOT NULL,
                release_year INTEGER,
                uri TEXT,
                url TEXT,
                FOREIGN KEY (artist_id) REFERENCES Artists(id)
            );
            
            CREATE TABLE IF NOT EXISTS Tracks (
                id TEXT PRIMARY KEY,
                artist_id TEXT NOT NULL,
                album_id TEXT NOT NULL,
                name TEXT NOT NULL,
                release_year INTEGER,
                uri TEXT,
                url TEXT,
                FOREIGN KEY (artist_id) REFERENCES Artists(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_albums_artist ON Albums(artist_id);
            CREATE INDEX IF NOT EXISTS idx_tracks_artist ON Tracks(artist_id);
        ''')
        
        # Migration: Add image_url column if it doesn't exist
        try:
            conn.execute("ALTER TABLE Artists ADD COLUMN image_url TEXT")
        except:
            pass  # Column already exists

def add_artist(artist_info):
    """Insert or update artist with genres as comma-separated string."""
    with get_connection() as conn:
        genres_str = ", ".join(artist_info.get("genres", []))
        # Get the best image URL (medium size preferred, fallback to largest available)
        images = artist_info.get("images", [])
        image_url = ""
        if images:
            # Sort by size, prefer medium size (~320px) or largest available
            sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
            image_url = sorted_images[0].get("url", "")
            # Prefer medium size if available (around 300-400px)
            for img in sorted_images:
                if 200 <= img.get("width", 0) <= 500:
                    image_url = img.get("url", "")
                    break
        
        conn.execute(
            "INSERT OR REPLACE INTO Artists (id, name, genres, uri, url, image_url) VALUES (?, ?, ?, ?, ?, ?)",
            (artist_info["artist_id"], artist_info["artist_name"], genres_str, 
             artist_info["uri"], artist_info["external_urls"].get("spotify", ""), image_url)
        )

def add_album(album_info):
    """Insert album record."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO Albums (id, artist_id, name, release_year, uri, url) VALUES (?, ?, ?, ?, ?, ?)",
            (album_info["album_id"], album_info["artist_id"], album_info["album_name"], 
             album_info["release_year"], album_info["album_uri"], album_info["url"])
        )

def add_track(track_info):
    """Insert track record."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO Tracks (id, artist_id, album_id, name, release_year, uri, url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (track_info["track_id"], track_info["artist_id"], track_info["album_id"], 
             track_info["track_name"], track_info["release_year"], track_info["track_uri"], track_info["url"])
        )

def get_all_items():
    """Get all albums and tracks with artist info."""
    with get_connection() as conn:
        albums = conn.execute("""
            SELECT 'album' as type, a.id, a.name, ar.name as artist_name, 
                   a.release_year, a.uri, a.url, ar.genres
            FROM Albums a JOIN Artists ar ON a.artist_id = ar.id
            ORDER BY ar.name, a.release_year
        """).fetchall()
        
        tracks = conn.execute("""
            SELECT 'track' as type, t.id, t.name, ar.name as artist_name, 
                   t.release_year, t.uri, t.url, ar.genres
            FROM Tracks t JOIN Artists ar ON t.artist_id = ar.id
            ORDER BY ar.name, t.name
        """).fetchall()
        
        return [dict(row) for row in albums + tracks]

def get_artists():
    """Get all artists."""
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM Artists ORDER BY name").fetchall()]

def get_artist_by_id(artist_id):
    """Get a single artist by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Artists WHERE id = ?", (artist_id,)).fetchone()
        return dict(row) if row else None

def get_albums():
    """Get all albums."""
    with get_connection() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT a.*, ar.name as artist_name 
            FROM Albums a 
            JOIN Artists ar ON a.artist_id = ar.id 
            ORDER BY ar.name, a.name
        """).fetchall()]

def get_album_by_id(album_id):
    """Get a single album by ID."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT a.*, ar.name as artist_name 
            FROM Albums a 
            JOIN Artists ar ON a.artist_id = ar.id 
            WHERE a.id = ?
        """, (album_id,)).fetchone()
        return dict(row) if row else None

def album_has_tracks(album_id):
    """Check if an album has any tracks in the database."""
    with get_connection() as conn:
        track_count = conn.execute("SELECT COUNT(*) as count FROM Tracks WHERE album_id = ?", (album_id,)).fetchone()['count']
        return track_count > 0

def delete_album(album_id):
    """Delete an album by ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM Albums WHERE id = ?", (album_id,))

def artist_has_content(artist_id):
    """Check if an artist has any tracks or albums in the database."""
    with get_connection() as conn:
        track_count = conn.execute("SELECT COUNT(*) as count FROM Tracks WHERE artist_id = ?", (artist_id,)).fetchone()['count']
        album_count = conn.execute("SELECT COUNT(*) as count FROM Albums WHERE artist_id = ?", (artist_id,)).fetchone()['count']
        return track_count > 0 or album_count > 0

def delete_artist(artist_id):
    """Delete an artist by ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM Artists WHERE id = ?", (artist_id,))

def delete_item(item_id, item_type):
    """Delete album or track by ID."""
    table = "Albums" if item_type == "album" else "Tracks"
    with get_connection() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))

def export_database_csv():
    """Export all database tables to a CSV file."""
    import csv
    tables = {
        "artists": ["id", "name", "genres", "uri", "url"],
        "albums": ["id", "artist_id", "name", "release_year", "uri", "url"],
        "tracks": ["id", "artist_id", "album_id", "name", "release_year", "uri", "url"]
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
        return export_file
    except Exception as e:
        raise e

def import_database_csv(import_file):
    """Import database data from a CSV file."""
    import csv
    
    try:
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
                        _insert_csv_data(current_table, headers, data)
                        data = []
                    current_table = row[0][1:-1]
                    headers = []
                elif not headers:
                    headers = row
                else:
                    data.append(row)
            
            if current_table and data:
                _insert_csv_data(current_table, headers, data)
                
    except Exception as e:
        raise e

def _insert_csv_data(table, columns, data):
    """Helper function to insert CSV data into specified table."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(columns))
            cursor.executemany(
                f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                data
            )
            conn.commit()
    except Exception as e:
        raise e

def cleanup_unused_artists():
    """Delete artists not linked to any tracks or albums."""
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
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        raise e
