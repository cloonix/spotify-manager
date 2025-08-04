# 🎵 Spotify Manager

A modern, lightweight web application for organizing and managing your favorite Spotify tracks, albums, and artists. Built with Flask, featuring a beautiful dark theme and intuitive user interface.

![Spotify Manager](https://img.shields.io/badge/Spotify-Manager-1DB954?style=for-the-badge&logo=spotify&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

## ✨ Features

### Core Functionality
- 🎶 **Quick Add**: Paste any Spotify URL (album/track) for instant import
- 📚 **Smart Browse**: Filter and search through your music collection
- 👥 **Artist Management**: Organize and explore your favorite artists
- 🏷️ **Genre Tagging**: Automatic genre categorization from Spotify
- 📊 **Collection Stats**: Track your music library growth

### User Experience
- 🌙 **Beautiful Dark Theme**: Easy on the eyes with Spotify-inspired design
- 📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- ⚡ **Real-time Search**: Instant filtering without page reloads
- 🚀 **Fast Performance**: Optimized architecture for speed
- 💾 **Data Management**: Export/import your collection as CSV

### Technical Features
- 🐳 **Docker Ready**: One-command deployment with Docker Compose
- 🔒 **Secure**: Environment-based configuration
- 🗄️ **SQLite Database**: Lightweight, file-based storage
- 🎨 **Modern Frontend**: Tailwind CSS with custom components
- 📦 **Optimized Code**: Clean, maintainable architecture

## 🚀 Quick Start

### Prerequisites
- [Spotify Developer Account](https://developer.spotify.com/)
- Docker & Docker Compose (recommended) **OR** Python 3.8+

### 1. Get Spotify API Credentials
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note your **Client ID** and **Client Secret**

### 2. Clone Repository
```bash
git clone https://github.com/your-username/spotify-manager.git
cd spotify-manager
```

### 3. Configure Environment
```bash
cp .env_sample .env
```

Edit `.env` with your Spotify credentials:
```env
SPOTIPY_CLIENT_ID=your_spotify_client_id_here
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret_here
SECRET_KEY=your_secret_key_here
DATABASE=/app/data/spotify_manager.db
```

## 🐳 Docker Deployment (Recommended)

### Quick Start with Docker
```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The application will be available at **http://localhost:5000**

### Docker Configuration

The included `docker-compose.yml` provides:
- **Persistent Data**: Volume mounting for database persistence
- **Environment Variables**: Secure credential management
- **Port Mapping**: Access on localhost:5000
- **Auto-restart**: Container restarts on failure

### Docker Commands
```bash
# Build and start services
docker-compose up --build

# Run in background
docker-compose up -d

# View application logs
docker-compose logs app

# Restart services
docker-compose restart

# Clean up (removes containers and volumes)
docker-compose down -v
```

## 💻 Local Development

### Setup Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Application
```bash
# Development mode (with auto-reload)
python app.py

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📖 Usage Guide

### Adding Music
1. **Quick Add** (Home Page):
   - Paste any Spotify URL in the main input field
   - Press Enter or click the add button
   - Automatically redirects to browse after successful addition

2. **Advanced Add** (Modal):
   - Click "Add Music" button in header or home page
   - Paste Spotify URL in the modal form
   - Add with additional options

### Browsing Collection
- **Filter by Type**: All, Albums, or Tracks
- **Search**: Real-time search across titles, artists, and genres
- **Sort**: Click column headers to sort
- **Actions**: Open in Spotify or delete items

### Managing Artists
- View all artists in your collection
- See genre information for each artist
- Quick actions to view artist details or search on Spotify

### Data Management
Access via Settings dropdown in header:
- **Export CSV**: Download your collection as CSV backup
- **Import CSV**: Restore from previously exported CSV
- **Download DB**: Download raw SQLite database file
- **Cleanup DB**: Remove unused artist entries

## 🛠️ Development

### Project Structure
```
spotify-manager/
├── app.py                 # Main Flask application
├── database.py           # Database operations and models
├── static/
│   ├── app.js            # Frontend JavaScript (centralized)
│   ├── styles.css        # Custom styles and Tailwind overrides
│   └── favicon.ico       # Application favicon
├── templates/
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Home page
│   ├── browse.html       # Music collection browser
│   ├── artists.html      # Artist management page
│   ├── import.html       # CSV import interface
│   └── macros.html       # Reusable Jinja2 macros
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile           # Docker container definition
├── requirements.txt     # Python dependencies
└── .env_sample         # Environment variables template
```

### Architecture Highlights

**Backend (Python/Flask)**:
- Clean route handlers with proper error handling
- Modular database operations
- Spotify Web API integration via spotipy
- CSV import/export functionality

**Frontend (HTML/CSS/JS)**:
- Tailwind CSS for rapid styling
- Vanilla JavaScript with class-based architecture
- Reusable Jinja2 macros for DRY templates
- Progressive enhancement (works without JS)

**Database (SQLite)**:
- Simple, file-based storage
- Normalized schema with proper relationships
- Automatic genre extraction and storage

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper commit messages
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

**Spotify API Errors**:
- Verify your Client ID and Client Secret in `.env`
- Ensure your Spotify app has proper permissions
- Check that URLs are valid Spotify links

**Database Issues**:
- Ensure the data directory is writable
- Check Docker volume permissions
- Verify DATABASE path in environment variables

**Docker Issues**:
- Run `docker-compose down -v` to clean up volumes
- Check Docker logs: `docker-compose logs app`
- Ensure ports 5000 is not in use

**Performance Issues**:
- Large collections may load slowly - consider pagination
- Database cleanup removes unused artists
- Clear browser cache if UI seems outdated

### Getting Help
- Check the [Issues](https://github.com/your-username/spotify-manager/issues) page
- Create a new issue with detailed error information
- Include relevant log output and environment details

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/) for music data
- [Spotipy](https://spotipy.readthedocs.io/) for Python Spotify integration
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Tailwind CSS](https://tailwindcss.com/) for styling utilities

---

**Made with ❤️ for music lovers**

*Organize your Spotify collection like never before!* 🎵✨