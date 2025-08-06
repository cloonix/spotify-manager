// Spotify Manager - Main Application JavaScript
class SpotifyManager {
    constructor() {
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.addMusicModal = document.getElementById('addMusicModal');
        this.addMusicForm = document.getElementById('addMusicForm');
        this.settingsMenu = document.getElementById('settingsMenu');
        this.mobileMenu = document.getElementById('mobileMenu');
    }

    bindEvents() {
        // Modal controls
        document.addEventListener('click', (e) => {
            if (e.target.matches('#addMusicBtn, [id*="addItemButton"]')) {
                e.preventDefault();
                this.openModal();
            }
            if (e.target.matches('#closeModal, #cancelAdd')) this.closeModal();
            if (e.target.id === 'settingsBtn') this.toggleSettings(e);
            if (e.target.id === 'mobileMenuBtn') this.toggleMobile();
        });

        // Form submissions
        this.addMusicForm?.addEventListener('submit', (e) => this.submitMusic(e));
        document.getElementById('quickAddForm')?.addEventListener('submit', (e) => this.quickAdd(e));

        // Close modals on escape/backdrop
        document.addEventListener('keydown', (e) => e.key === 'Escape' && this.closeModal());
        this.addMusicModal?.addEventListener('click', (e) => e.target === this.addMusicModal && this.closeModal());
        
        // Close settings menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#settingsBtn') && !e.target.closest('#settingsMenu')) {
                this.settingsMenu?.classList.add('hidden');
            }
        });

        // Auto-paste detection
        document.getElementById('quickSpotifyUrl')?.addEventListener('paste', () => {
            setTimeout(() => {
                const input = document.getElementById('quickSpotifyUrl');
                if (input.value.includes('spotify.com')) {
                    setTimeout(() => document.getElementById('quickAddForm').dispatchEvent(new Event('submit')), 500);
                }
            }, 100);
        });
    }

    openModal() {
        this.addMusicModal.classList.remove('hidden');
        setTimeout(() => document.getElementById('spotifyUrl')?.focus(), 100);
    }

    closeModal() {
        this.addMusicModal.classList.add('hidden');
        this.addMusicForm?.reset();
    }

    toggleSettings(e) {
        e.stopPropagation();
        this.settingsMenu.classList.toggle('hidden');
    }

    toggleMobile() {
        this.mobileMenu?.classList.toggle('hidden');
    }

    async submitMusic(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const btn = e.target.querySelector('button[type="submit"]');
        
        this.setLoading(btn, true);
        
        try {
            const response = await fetch('/add', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.success, 'success');
                this.closeModal();
                if (window.location.pathname === '/browse') {
                    setTimeout(() => window.location.reload(), 1000);
                }
            } else {
                this.showMessage(data.error, 'error');
            }
        } catch (error) {
            this.showMessage('Failed to add music. Please try again.', 'error');
        } finally {
            this.setLoading(btn, false);
        }
    }

    async quickAdd(e) {
        e.preventDefault();
        const url = e.target.querySelector('input[name="spotify_url"]').value.trim();
        
        if (!url) {
            this.showMessage('Please enter a Spotify URL', 'error');
            return;
        }

        const btn = e.target.querySelector('button[type="submit"]');
        this.setLoading(btn, true);

        try {
            const formData = new FormData();
            formData.append('spotify_url', url);
            
            const response = await fetch('/add', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.success, 'success');
                e.target.reset();
                setTimeout(() => window.location.href = '/browse', 1500);
            } else {
                this.showMessage(data.error, 'error');
            }
        } catch (error) {
            this.showMessage('Failed to add music. Please try again.', 'error');
        } finally {
            this.setLoading(btn, false);
        }
    }

    setLoading(btn, loading) {
        if (loading) {
            btn.dataset.originalText = btn.innerHTML;
            btn.innerHTML = '<div class="loading"></div>';
            btn.disabled = true;
        } else {
            btn.innerHTML = btn.dataset.originalText;
            btn.disabled = false;
        }
    }

    showMessage(message, type) {
        const container = document.getElementById('messages');
        const div = document.createElement('div');
        div.className = `message message-${type}`;
        div.textContent = message;
        container.appendChild(div);
        
        setTimeout(() => {
            div.style.transform = 'translateX(100%)';
            div.style.opacity = '0';
            setTimeout(() => div.remove(), 300);
        }, 5000);
    }

    // Utility functions for browse page
    static initSearch(inputId, itemSelector) {
        const input = document.getElementById(inputId);
        const items = document.querySelectorAll(itemSelector);
        
        input?.addEventListener('input', function() {
            const term = this.value.toLowerCase();
            items.forEach(item => {
                const searchData = item.dataset.search || item.textContent.toLowerCase();
                item.style.display = searchData.includes(term) ? '' : 'none';
            });
        });
    }

    static async deleteItem(type, id) {
        const itemName = type === 'album' ? 'album' : 'track';
        
        if (!confirm(`Delete this ${itemName}?\n\nThis will remove it from both your local database and Spotify library to keep everything in sync.`)) return;

        try {
            const response = await fetch(`/delete/${type}/${id}`, { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                app.showMessage(data.success, 'success');
                
                // Show warning if Spotify removal failed
                if (data.warning) {
                    setTimeout(() => app.showMessage(data.warning, 'warning'), 2000);
                }
                
                // Remove the row from the table
                const row = document.querySelector(`tr[data-id="${id}"]`);
                if (row) {
                    row.remove();
                }
                
                // Update counts if elements exist
                setTimeout(() => {
                    const countElements = document.querySelectorAll('[id*="count"], [class*="count"]');
                    countElements.forEach(el => {
                        const currentText = el.textContent;
                        const match = currentText.match(/(\d+)/);
                        if (match) {
                            const newCount = Math.max(0, parseInt(match[1]) - 1);
                            el.textContent = currentText.replace(/\d+/, newCount);
                        }
                    });
                }, 100);
            } else {
                app.showMessage(data.error, 'error');
            }
        } catch (error) {
            app.showMessage('Failed to delete item', 'error');
        }
    }

    static async cleanupDatabase() {
        if (!confirm('This will remove unused artists from your database. Continue?')) return;
        
        try {
            const response = await fetch('/cleanup', { method: 'POST' });
            const data = await response.json();
            app.showMessage(data.success || data.error, data.success ? 'success' : 'error');
        } catch (error) {
            app.showMessage('Network error during cleanup', 'error');
        }
        
        document.getElementById('settingsMenu').classList.add('hidden');
    }
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new SpotifyManager();
    
    // Auto-focus on home page
    document.getElementById('quickSpotifyUrl')?.focus();
    
    // Initialize search if on browse/artists page
    SpotifyManager.initSearch('searchInput', '.music-row');
    SpotifyManager.initSearch('artistSearch', '.artist-card');
    
    // Initialize import page if present
    SpotifyManager.initImport();
    
    // Initialize artist modal if present
    SpotifyManager.initArtistModal();
});

// Import page specific functionality
SpotifyManager.initImport = function() {
        const fileInput = document.getElementById('file');
        const fileName = document.getElementById('fileName');
        const dropZone = document.querySelector('.border-dashed');
        
        if (!fileInput || !dropZone) return;
        
        // File selection handler
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileName.textContent = `Selected: ${this.files[0].name}`;
                fileName.classList.remove('hidden');
            } else {
                fileName.classList.add('hidden');
            }
        });
        
        // Drag and drop handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('border-spotify'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-spotify'), false);
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        }, false);
};

// Artist modal functionality
SpotifyManager.viewArtistDetails = function(artistId, artistName) {
    const modal = document.getElementById('artistModal');
    const title = document.getElementById('artistModalTitle');
    const content = document.getElementById('artistModalContent');
    
    if (!modal) return;
    
    title.textContent = artistName;
    content.innerHTML = '<div class="text-center text-gray-400 py-8">Loading artist details...</div>';
    modal.classList.remove('hidden');
    
    // Fetch detailed artist information
    fetch(`/artist-details/${artistId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                content.innerHTML = `<div class="text-center text-red-400 py-8">${data.error}</div>`;
                return;
            }
            
            content.innerHTML = `
                <div class="space-y-6">
                    <div class="text-center">
                        ${data.image_url ? 
                            `<img src="${data.image_url}" alt="${data.name}" class="w-32 h-32 rounded-full mx-auto mb-4 object-cover shadow-lg">` :
                            `<div class="w-32 h-32 bg-gradient-spotify rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
                                <svg class="w-16 h-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                                </svg>
                            </div>`
                        }
                        <h4 class="text-2xl font-bold text-white mb-2">${data.name}</h4>
                        ${data.is_following ? 
                            '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-spotify text-white">Following</span>' :
                            '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-dark-600 text-gray-300">Not Following</span>'
                        }
                    </div>
                    
                    ${data.followers > 0 || data.popularity > 0 ? `
                    <div class="grid grid-cols-2 gap-4">
                        <div class="text-center p-4 bg-dark-700 rounded-lg">
                            <div class="text-2xl font-bold text-spotify">${data.followers.toLocaleString()}</div>
                            <div class="text-sm text-gray-400">Followers</div>
                        </div>
                        <div class="text-center p-4 bg-dark-700 rounded-lg">
                            <div class="text-2xl font-bold text-accent-400">${data.popularity}%</div>
                            <div class="text-sm text-gray-400">Popularity</div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.genres ? `
                    <div class="bg-dark-700 rounded-lg p-4">
                        <h5 class="font-semibold text-white mb-3">Genres</h5>
                        <div class="flex flex-wrap gap-2">
                            ${data.genres.split(', ').map(genre => 
                                `<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-dark-600 text-gray-300 border border-dark-500">${genre}</span>`
                            ).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="bg-dark-700 rounded-lg p-4">
                        <h5 class="font-semibold text-white mb-3">Quick Actions</h5>
                        <div class="space-y-3">
                            <a href="/browse?search=${encodeURIComponent(data.name)}" 
                               class="flex items-center text-spotify hover:text-green-400 transition-colors">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-1v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-1"/>
                                </svg>
                                View all tracks by this artist
                            </a>
                            <button onclick="searchSpotify('${data.name}')" 
                                    class="flex items-center text-accent-400 hover:text-accent-300 transition-colors">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                </svg>
                                Search on Spotify
                            </button>
                            ${data.spotify_url ? `
                            <a href="${data.spotify_url}" target="_blank" 
                               class="flex items-center text-gray-400 hover:text-white transition-colors">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                                </svg>
                                Open in Spotify
                            </a>
                            ` : ''}
                            ${data.is_following ? `
                            <button onclick="unfollowArtistFromModal('${data.id}', '${data.name}')" 
                                    class="flex items-center text-red-400 hover:text-red-300 transition-colors">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                                </svg>
                                Unfollow on Spotify
                            </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            content.innerHTML = '<div class="text-center text-red-400 py-8">Failed to load artist details</div>';
        });
};

SpotifyManager.searchSpotify = function(artistName) {
    window.open(`https://open.spotify.com/search/${encodeURIComponent(artistName)}`, '_blank');
};

SpotifyManager.initArtistModal = function() {
    const closeBtn = document.getElementById('closeArtistModal');
    const modal = document.getElementById('artistModal');
    
    if (!modal) return;
    
    closeBtn?.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
};

// Global functions for templates
window.deleteItem = SpotifyManager.deleteItem;
window.cleanupDatabase = SpotifyManager.cleanupDatabase;
window.updateFileName = (input) => {
    const fileName = document.getElementById('fileName');
    if (input.files.length > 0) {
        fileName.textContent = `Selected: ${input.files[0].name}`;
        fileName.classList.remove('hidden');
    } else {
        fileName.classList.add('hidden');
    }
};
window.viewArtistDetails = SpotifyManager.viewArtistDetails;
window.searchSpotify = SpotifyManager.searchSpotify;

// Unfollow artist from modal
window.unfollowArtistFromModal = async function(artistId, artistName) {
    if (!confirm(`Are you sure you want to unfollow ${artistName} on Spotify?`)) return;
    
    try {
        const response = await fetch(`/unfollow-artist/${artistId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            app?.showMessage(data.success, 'success');
            // Close modal and refresh page if on artists page
            document.getElementById('artistModal').classList.add('hidden');
            if (window.location.pathname === '/artists') {
                setTimeout(() => window.location.reload(), 1000);
            }
        } else {
            app?.showMessage(data.error || 'Failed to unfollow artist', 'error');
        }
    } catch (error) {
        app?.showMessage('Network error occurred', 'error');
    }
};

// View album details
window.viewAlbumDetails = async function(albumId) {
    try {
        const response = await fetch(`/album-details/${albumId}`);
        const data = await response.json();
        
        if (data.error) {
            app?.showMessage(data.error, 'error');
            return;
        }
        
        // Populate the modal with album data
        document.getElementById('albumDetails').innerHTML = `
            <div class="sm:flex sm:items-start">
                <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <div class="flex items-center space-x-4 mb-4">
                        ${data.image_url ? `<img src="${data.image_url}" alt="${data.name}" class="w-16 h-16 rounded-lg object-cover"/>` : ''}
                        <div>
                            <h3 class="text-lg leading-6 font-medium text-white">${data.name}</h3>
                            <p class="text-sm text-gray-400">by ${data.artist_name}</p>
                        </div>
                    </div>
                    
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Release Year:</span>
                            <span class="text-white">${data.release_year}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Total Tracks:</span>
                            <span class="text-white">${data.total_tracks}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Popularity:</span>
                            <span class="text-white">${data.popularity}/100</span>
                        </div>
                    </div>
                    
                    <div class="mt-4 flex space-x-2">
                        <a href="${data.spotify_url}" target="_blank" 
                           class="inline-flex items-center px-3 py-2 border border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-300 bg-dark-600 hover:bg-dark-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-spotify">
                            <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
                            </svg>
                            Open in Spotify
                        </a>
                        ${data.is_saved ? `
                            <button onclick="unsaveAlbumFromModal('${data.id}', '${data.name}', '${data.artist_name}')" 
                                    class="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                                Remove from Library
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Show the modal
        document.getElementById('albumModal').classList.remove('hidden');
        
    } catch (error) {
        app?.showMessage('Failed to load album details', 'error');
    }
};

// Unsave album from modal
window.unsaveAlbumFromModal = async function(albumId, albumName, artistName) {
    if (!confirm(`Are you sure you want to remove "${albumName}" by ${artistName} from your saved albums?`)) return;
    
    try {
        const response = await fetch(`/unsave-album/${albumId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            app?.showMessage(data.success, 'success');
            // Close modal and refresh page if on browse page
            document.getElementById('albumModal').classList.add('hidden');
            if (window.location.pathname === '/browse') {
                setTimeout(() => window.location.reload(), 1000);
            }
        } else {
            app?.showMessage(data.error || 'Failed to unsave album', 'error');
        }
    } catch (error) {
        app?.showMessage('Network error occurred', 'error');
    }
};

// Helper function for sync operations
async function performSync(endpoint, confirmMessage, successRefresh = false) {
    if (!confirm(confirmMessage)) return;
    
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            app.showMessage(data.success, 'success');
            if (successRefresh) {
                setTimeout(() => window.location.reload(), 2000);
            }
        } else {
            app.showMessage(data.error, 'error');
        }
        
        // Close settings menu
        document.getElementById('settingsMenu').classList.add('hidden');
    } catch (error) {
        app.showMessage('Network error during sync', 'error');
        document.getElementById('settingsMenu').classList.add('hidden');
    }
}

// Sync all Spotify data
window.syncAllSpotify = async function() {
    await performSync(
        '/sync-all-spotify',
        'This will sync ALL your Spotify data (followed artists, saved albums, and saved tracks). This may take a while. Continue?',
        true
    );
};

// Sync followed artists from Spotify
window.syncFollowedArtists = async function() {
    await performSync(
        '/sync-followed-artists',
        'This will sync all your followed artists from Spotify. Continue?',
        window.location.pathname === '/artists'
    );
};

// Sync saved albums from Spotify
window.syncSavedAlbums = async function() {
    await performSync(
        '/sync-saved-albums',
        'This will sync all your saved albums from Spotify. Continue?',
        window.location.pathname === '/browse'
    );
};

// Sync saved tracks from Spotify
window.syncSavedTracks = async function() {
    await performSync(
        '/sync-saved-tracks',
        'This will sync all your saved tracks from Spotify. Continue?',
        window.location.pathname === '/browse'
    );
};