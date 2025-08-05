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
        if (!confirm(`Are you sure you want to delete this ${type}?`)) return;
        
        const row = document.querySelector(`[data-id="${id}"][data-type="${type}"]`);
        row.style.opacity = '0.5';
        row.style.pointerEvents = 'none';
        
        try {
            const response = await fetch(`/delete/${type}/${id}`, { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                row.style.transform = 'translateX(100%)';
                setTimeout(() => row.remove(), 300);
                app.showMessage(data.success, 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            row.style.opacity = '1';
            row.style.pointerEvents = 'auto';
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
    
    setTimeout(() => {
        content.innerHTML = `
            <div class="space-y-4">
                <div class="text-center">
                    <div class="w-20 h-20 bg-gradient-spotify rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                        </svg>
                    </div>
                    <h4 class="text-xl font-bold text-white mb-2">${artistName}</h4>
                </div>
                
                <div class="bg-dark-700 rounded-lg p-4">
                    <h5 class="font-semibold text-white mb-2">Quick Actions</h5>
                    <div class="space-y-2">
                        <a href="/browse?search=${encodeURIComponent(artistName)}" class="block text-spotify hover:text-green-400 transition-colors">
                            → View all tracks by this artist
                        </a>
                        <button onclick="searchSpotify('${artistName}')" class="block text-accent-400 hover:text-accent-300 transition-colors">
                            → Search on Spotify
                        </button>
                    </div>
                </div>
                
                <div class="text-sm text-gray-400 text-center">
                    More detailed artist analytics coming soon!
                </div>
            </div>
        `;
    }, 500);
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