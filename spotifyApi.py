import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os

load_dotenv()

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    )
)


def get_album_info(spotify_url):
    """
    Fetches album information from Spotify API.
    :param spotify_url: URL of the Spotify album
    :return: Tuple containing album_id, artist_id, album_name, artist_name, release_year, album_uri
    """
    album_id = spotify_url.split("/")[-1].split("?")[0]
    album = sp.album(album_id)

    artist_id = album["artists"][0]["id"]
    album_name = album["name"]
    release_year = album["release_date"].split("-")[0]
    album_uri = album["uri"]

    return album_id, artist_id, album_name, release_year, album_uri


def get_track_info(spotify_url):
    """
    Fetches track information from Spotify API.
    :param spotify_url: URL of the Spotify track
    :return: Tuple containing track_id, artist_id, album_id, track_name, release_year, track_uri
    """
    track_id = spotify_url.split("/")[-1].split("?")[0]
    track = sp.track(track_id)

    artist_id = track["artists"][0]["id"]
    album_id = track["album"]["id"]
    track_name = track["name"]
    release_year = track["album"]["release_date"].split("-")[0]
    track_uri = track["uri"]

    return track_id, artist_id, album_id, track_name, release_year, track_uri


def get_artist_info(artist_id):
    """
    Fetches artist information from Spotify API.
    :param artist_id: The Spotify artist's ID
    :return: Tuple containing artist_id, artist_name, genres, uri, external_urls
    """
    artist = sp.artist(artist_id)
    return (
        artist["id"],
        artist["name"],
        artist["genres"],
        artist["uri"],
        artist["external_urls"],
    )
