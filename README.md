# Spotify Manager

A simple, lightweight web app to organize your favorite Spotify albums and tracks.

## Features

- ✅ Add albums & tracks by pasting Spotify URLs
- ✅ Browse your collection with filtering
- ✅ Clean, dark-themed interface  
- ✅ Artist and genre organization
- ✅ Docker deployment ready

## Quick Start

1. **Get Spotify API credentials** from [developer.spotify.com](https://developer.spotify.com/)

2. **Clone and setup**:
   ```bash
   git clone <repo-url>
   cd spotify-manager
   cp .env_sample .env
   # Edit .env with your credentials
   ```

3. **Run with Docker**:
   ```bash
   docker-compose up
   ```

4. **Or run locally**:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

5. **Open** [http://localhost:5000](http://localhost:5000)

## Usage

1. Click **"+ Add Music"** 
2. Paste any Spotify album/track URL
3. Browse your collection on the **Browse** page
4. Filter by Albums or Tracks as needed

That's it! 🎵
