// DECTERUM - JavaScript Application Logic

// Application state
let currentUser = null;
let contacts = [];
let activeContact = null;
let messages = [];
let isConnected = false;
let activeSection = 'chat';

// Initialization
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadUserData();
    startPeriodicUpdates();
});

function setupEventListeners() {
    // Enter to send message
    const messageInput = document.getElementById('message-input');
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Close modals when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideAllModals();
            }
        });
    });
}

async function loadUserData() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            currentUser = await response.json();
            updateUserDisplay();
        }
        
        await loadContacts();
        await loadNetworkInfo();
        updateConnectionStatus();
    } catch (error) {
        console.error('Error loading data:', error);
        updateConnectionStatus(false);
    }
}

function updateUserDisplay() {
    if (currentUser) {
        document.getElementById('user-username').textContent = currentUser.username;
        // Show full User ID, don't truncate
        document.getElementById('user-id').textContent = currentUser.user_id;
        document.getElementById('user-id').title = currentUser.user_id; // Tooltip with full ID
        document.getElementById('profile-username').value = currentUser.username;
    }
}

async function loadNetworkInfo() {
    try {
        const response = await fetch('/api/network-info');
        if (response.ok) {
            const data = await response.json();
            
            document.getElementById('network-status').textContent = 
                data.network_status === 'online' ? 'Online' : 'Offline';
            document.getElementById('peers-count').textContent = data.peers_connected;
            document.getElementById('local-port').textContent = data.local_port;
            
            if (data.tunnel_active && data.tunnel_url) {
                document.getElementById('tunnel-status').textContent = 'Active';
                document.getElementById('tunnel-url').textContent = data.tunnel_url;
                document.getElementById('tunnel-url-item').style.display = 'flex';
            } else {
                document.getElementById('tunnel-status').textContent = 'Disabled';
                document.getElementById('tunnel-url-item').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading network info:', error);
    }
}

async function loadContacts() {
    try {
        const response = await fetch('/api/contacts');
        if (response.ok) {
            const data = await response.json();
            contacts = data.contacts;
            renderContacts();
        }
    } catch (error) {
        console.error('Error loading contacts:', error);
    }
}

function renderContacts() {
    const contactsList = document.getElementById('contacts-list');
    
    if (contacts.length === 0) {
        contactsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <h3>No conversations</h3>
                <p>Add contacts to start messaging</p>
            </div>
        `;
        return;
    }

    const contactsHTML = contacts.map(contact => `
        <div class="contact-item ${activeContact?.contact_id === contact.contact_id ? 'active' : ''}" 
             onclick="selectContact('${contact.contact_id}')">
            <div class="contact-avatar">
                ${contact.username.charAt(0).toUpperCase()}
            </div>
            <div class="contact-info">
                <div class="contact-name">${contact.username}</div>
                <div class="contact-preview">
                    ${contact.status === 'online' ? 'Online' : 'Tap to message'}
                </div>
            </div>
            <div class="contact-time">
                ${new Date(contact.added_at * 1000).toLocaleDateString()}
            </div>
        </div>
    `).join('');

    contactsList.innerHTML = contactsHTML;
}

async function selectContact(contactId) {
    activeContact = contacts.find(c => c.contact_id === contactId);
    if (!activeContact) return;

    // Show chat view
    document.getElementById('contacts-view').classList.add('hidden');
    document.getElementById('chat-view').classList.remove('hidden');
    
    // Update chat header
    document.getElementById('chat-contact-name').textContent = activeContact.username;
    
    // Enable input
    document.getElementById('message-input').disabled = false;
    document.getElementById('send-btn').disabled = false;
    document.getElementById('message-input').placeholder = `Message ${activeContact.username}...`;

    // Load messages
    await loadMessages(contactId);
    
    // Update contacts list
    renderContacts();
}

function showContactsList() {
    document.getElementById('chat-view').classList.add('hidden');
    document.getElementById('contacts-view').classList.remove('hidden');
    
    // Disable input
    document.getElementById('message-input').disabled = true;
    document.getElementById('send-btn').disabled = true;
    
    activeContact = null;
    renderContacts();
}

async function loadMessages(contactId = null) {
    try {
        const url = contactId ? `/api/messages?contact_id=${contactId}` : '/api/messages';
        const response = await fetch(url);
        
        if (response.ok) {
            const data = await response.json();
            messages = data.messages;
            renderMessages();
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

function renderMessages() {
    const messagesContainer = document.getElementById('messages-container');
    
    if (messages.length === 0) {
        messagesContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <h3>Start a conversation</h3>
                <p>Type a message to begin</p>
            </div>
        `;
        return;
    }

    const messagesHTML = messages.map(msg => `
        <div class="message ${msg.sender_id === currentUser.user_id ? 'own' : ''}">
            <div class="message-bubble">
                <div>${escapeHtml(msg.content)}</div>
                <div class="message-time">${msg.formatted_time}</div>
            </div>
        </div>
    `).join('');

    messagesContainer.innerHTML = messagesHTML;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (!content || !activeContact) return;

    try {
        const response = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: content,
                recipient_id: activeContact.contact_id
            })
        });

        if (response.ok) {
            input.value = '';
            input.style.height = 'auto';
            await loadMessages(activeContact.contact_id);
        } else {
            const error = await response.json();
            showToast('Error sending message: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showToast('Connectivity error', 'error');
    }
}

async function addContact(event) {
    event.preventDefault();
    
    const contactId = document.getElementById('contact-id').value.trim();
    const contactName = document.getElementById('contact-name').value.trim();

    try {
        const response = await fetch('/api/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contact_id: contactId,
                username: contactName
            })
        });

        if (response.ok) {
            hideAddContactModal();
            await loadContacts();
            showToast('Contact added successfully!', 'success');
            
            // Select the added contact
            setTimeout(() => selectContact(contactId), 100);
        } else {
            const error = await response.json();
            showToast('Error adding contact: ' + error.detail, 'error');
        }
    } catch (error) {
        console.error('Error adding contact:', error);
        showToast('Connectivity error', 'error');
    }
}

async function updateProfile(event) {
    event.preventDefault();
    
    const username = document.getElementById('profile-username').value.trim();

    try {
        const response = await fetch('/api/user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username })
        });

        if (response.ok) {
            hideEditProfileModal();
            await loadUserData();
            showToast('Profile updated successfully!', 'success');
        } else {
            showToast('Error updating profile', 'error');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showToast('Connectivity error', 'error');
    }
}

async function discoverPeers() {
    try {
        const response = await fetch('/api/discover', { method: 'POST' });
        if (response.ok) {
            const data = await response.json();
            showToast(`Discovery completed: ${data.peers_found} nodes found`, 'success');
            await loadNetworkInfo();
        }
    } catch (error) {
        console.error('Error discovering peers:', error);
        showToast('Connectivity error', 'error');
    }
}

function switchSection(sectionName) {
    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionName + '-section').classList.add('active');

    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.nav-item').classList.add('active');

    // If returning to chat, show contacts list
    if (sectionName === 'chat') {
        showContactsList();
    }

    // Load feed module when switching to feed section
    if (sectionName === 'feed') {
        loadFeedModule();
    }

    activeSection = sectionName;
}

// Carrega módulo do feed
async function loadFeedModule() {
    try {
        const feedSection = document.getElementById('feed-section');

        // Se o módulo já foi carregado, apenas inicializa
        if (window.DECTERUM.ModuleLoader && window.DECTERUM.ModuleLoader.isModuleLoaded('feed')) {
            if (window.DECTERUM.Feed) {
                // Atualiza username se necessário
                const feedUsername = document.getElementById('feed-username');
                if (feedUsername && feedUsername.textContent === 'User' && currentUser) {
                    feedUsername.textContent = currentUser.username;
                }
                return;
            }
        }

        // Carrega o módulo completo
        if (window.DECTERUM.ModuleLoader) {
            await window.DECTERUM.ModuleLoader.loadModule('feed', feedSection);

            // Atualiza username após carregamento
            setTimeout(() => {
                const feedUsername = document.getElementById('feed-username');
                if (feedUsername && currentUser) {
                    feedUsername.textContent = currentUser.username;
                }
            }, 100);
        }
    } catch (error) {
        console.error('Erro carregando módulo do feed:', error);
        document.getElementById('feed-section').innerHTML = `
            <div class="empty-feed">
                <div class="empty-feed-icon">⚠️</div>
                <h3>Erro ao carregar feed</h3>
                <p>Tente recarregar a página</p>
            </div>
        `;
    }
}

function showAddContactModal() {
    document.getElementById('add-contact-modal').classList.add('show');
    document.getElementById('contact-id').focus();
}

function hideAddContactModal() {
    document.getElementById('add-contact-modal').classList.remove('show');
    document.getElementById('contact-id').value = '';
    document.getElementById('contact-name').value = '';
}

function showEditProfileModal() {
    document.getElementById('edit-profile-modal').classList.add('show');
    document.getElementById('profile-username').focus();
}

function hideEditProfileModal() {
    document.getElementById('edit-profile-modal').classList.remove('show');
}

function hideAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('show');
    });
}

// Copy Functions
async function copyUserId() {
    if (!currentUser) return;
    
    try {
        await navigator.clipboard.writeText(currentUser.user_id);
        showToast('User ID copied to clipboard!', 'success');
    } catch (error) {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(currentUser.user_id);
        showToast('User ID copied to clipboard!', 'success');
    }
}

async function copyTunnelUrl() {
    const tunnelUrl = document.getElementById('tunnel-url').textContent;
    if (tunnelUrl === '—') return;
    
    try {
        await navigator.clipboard.writeText(tunnelUrl);
        showToast('Tunnel URL copied to clipboard!', 'success');
    } catch (error) {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(tunnelUrl);
        showToast('Tunnel URL copied to clipboard!', 'success');
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    
    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
    }

    document.body.removeChild(textArea);
}

// Toast Notification System
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    toastMessage.textContent = message;
    
    // Add type-specific styling if needed
    toast.className = 'toast show';
    if (type === 'error') {
        toast.style.background = '#dc2626';
    } else if (type === 'success') {
        toast.style.background = '#16a34a';
    } else {
        toast.style.background = '#374151';
    }
    
    // Hide after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

async function updateConnectionStatus(connected = null) {
    if (connected === null) {
        try {
            const response = await fetch('/api/status');
            connected = response.ok;
        } catch {
            connected = false;
        }
    }

    isConnected = connected;
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    if (connected) {
        statusDot.classList.remove('offline');
        statusText.textContent = 'Online';
    } else {
        statusDot.classList.add('offline');
        statusText.textContent = 'Offline';
    }
}

function startPeriodicUpdates() {
    // Update every 10 seconds
    setInterval(async () => {
        if (activeContact && activeSection === 'chat') {
            await loadMessages(activeContact.contact_id);
        }
        await updateConnectionStatus();
        
        if (activeSection === 'settings') {
            await loadNetworkInfo();
        }
    }, 10000);
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Feed module loading is handled by the modular system

// Export functions for global access (if needed)
window.DECTERUM = window.DECTERUM || {};
Object.assign(window.DECTERUM, {
    copyUserId,
    copyTunnelUrl,
    showToast,
    switchSection,
    showAddContactModal,
    hideAddContactModal,
    showEditProfileModal,
    hideEditProfileModal,
    sendMessage,
    addContact,
    updateProfile,
    discoverPeers,
    selectContact,
    showContactsList,
    loadFeedModule
});