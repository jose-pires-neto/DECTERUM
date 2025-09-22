/**
 * DECTERUM Feed Module
 * Sistema de feed social descentralizado
 */

// Namespace para o módulo Feed
window.DECTERUM = window.DECTERUM || {};
window.DECTERUM.Feed = (function() {
    'use strict';

    // Estado privado do módulo
    let state = {
        posts: [],
        offset: 0,
        currentTab: 'home',
        isLoading: false,
        currentPostId: null,
        currentUser: null,
        initialized: false
    };

    // Configurações
    const config = {
        postsPerPage: 20,
        maxPostLength: 280,
        maxCommentLength: 280
    };

    // Elementos DOM (cache)
    let elements = {};

    /**
     * Inicialização do módulo
     */
    function init() {
        if (state.initialized) return;

        cacheElements();
        setupEventListeners();
        loadCurrentUser();
        loadFeed();
        setupInfiniteScroll();

        state.initialized = true;
        console.log('🔥 Feed module initialized - Twitter/X style');
    }

    /**
     * Cache dos elementos DOM
     */
    function cacheElements() {
        elements = {
            feedPosts: document.getElementById('feed-posts'),
            loadMoreContainer: document.getElementById('load-more-container'),
            commentContent: document.getElementById('comment-content'),
            commentCharCount: document.getElementById('comment-char-count'),
            commentBtn: document.getElementById('comment-btn'),
            commentsList: document.getElementById('comments-list'),
            quoteContent: document.getElementById('quote-content'),
            quoteCharCount: document.getElementById('quote-char-count'),
            quotedPostPreview: document.getElementById('quoted-post-preview'),
            quoteSubmitBtn: document.getElementById('quote-submit-btn'),
            // Modal elements
            modalPostContent: document.getElementById('modal-post-content'),
            modalCharCount: document.getElementById('modal-char-count'),
            modalCharProgress: document.getElementById('modal-char-progress'),
            modalPostBtn: document.getElementById('modal-post-btn'),
            modalUsername: document.getElementById('modal-username'),
            modalUserHandle: document.getElementById('modal-user-handle'),
            // FAB elements
            fabMain: document.getElementById('fab-main'),
            fabMenu: document.getElementById('fab-menu'),
            fabIcon: document.getElementById('fab-icon'),
            // Search elements
            searchInput: document.getElementById('search-input'),
            searchResults: document.getElementById('search-results'),
            // Profile elements
            profileUsername: document.getElementById('profile-username'),
            profileUserHandle: document.getElementById('profile-user-handle'),
            profilePosts: document.getElementById('profile-posts')
        };
    }

    /**
     * Configuração dos event listeners
     */
    function setupEventListeners() {
        // Modal post creation form
        if (elements.modalPostContent) {
            elements.modalPostContent.addEventListener('input', function() {
                const length = this.value.length;
                updateCharCounter(length, config.maxPostLength, elements.modalCharCount, elements.modalCharProgress);
                elements.modalPostBtn.disabled = length === 0 || length > config.maxPostLength;

                // Auto-resize
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 300) + 'px';
            });

            // Suporte para Ctrl+Enter
            elements.modalPostContent.addEventListener('keydown', function(e) {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    if (!elements.modalPostBtn.disabled) {
                        createPostFromModal();
                    }
                }
            });
        }

        // Search input
        if (elements.searchInput) {
            elements.searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    performSearch();
                }
            });

            elements.searchInput.addEventListener('input', function() {
                if (this.value.trim()) {
                    performSearch();
                }
            });
        }

        // Click outside modals to close
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal')) {
                closeAllModals();
            }
        });

        // Close modals with escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeAllModals();
                closeFabMenu();
            }
        });

        // Quote retweet form
        if (elements.quoteContent) {
            elements.quoteContent.addEventListener('input', function() {
                const length = this.value.length;
                elements.quoteCharCount.textContent = config.maxPostLength - length;
                elements.quoteSubmitBtn.disabled = length > config.maxPostLength;

                // Auto-resize
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 200) + 'px';
            });
        }

        // Comment form
        if (elements.commentContent) {
            elements.commentContent.addEventListener('input', function() {
                const length = this.value.length;
                elements.commentCharCount.textContent = `${length}/${config.maxCommentLength}`;
                elements.commentBtn.disabled = length === 0 || length > config.maxCommentLength;
            });
        }
    }

    /**
     * Carrega usuário atual
     */
    async function loadCurrentUser() {
        try {
            const response = await fetch('/api/user');
            if (response.ok) {
                const userData = await response.json();
                state.currentUser = userData;
                updateUserDisplay(userData);
            } else {
                // Usar dados padrão
                const defaultUser = {
                    username: 'User',
                    user_id: 'guest'
                };
                state.currentUser = defaultUser;
                updateUserDisplay(defaultUser);
            }
        } catch (error) {
            console.error('Erro carregando usuário:', error);
            const defaultUser = {
                username: 'User',
                user_id: 'guest'
            };
            state.currentUser = defaultUser;
            updateUserDisplay(defaultUser);
        }
    }

    /**
     * Atualiza exibição do usuário
     */
    function updateUserDisplay(user) {
        // Update modal user info
        if (elements.modalUsername) {
            elements.modalUsername.textContent = user.username;
        }
        if (elements.modalUserHandle) {
            elements.modalUserHandle.textContent = `@${user.username.toLowerCase()}`;
        }
        // Update profile info
        if (elements.profileUsername) {
            elements.profileUsername.textContent = user.username;
        }
        if (elements.profileUserHandle) {
            elements.profileUserHandle.textContent = `@${user.username.toLowerCase()}`;
        }
    }

    /**
     * Cria um novo post
     */
    async function createPostFromModal() {
        const content = elements.modalPostContent.value.trim();

        if (!content) return;

        try {
            // Desabilitar botão durante envio
            elements.modalPostBtn.disabled = true;
            elements.modalPostBtn.textContent = 'Postando...';

            const postData = {
                content: content,
                post_type: 'text'
            };

            const response = await fetch('/api/feed/posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(postData)
            });

            if (response.ok) {
                const data = await response.json();
                showToast('Post publicado!');

                // Clear form and close modal
                elements.modalPostContent.value = '';
                updateCharCounter(0, config.maxPostLength, elements.modalCharCount, elements.modalCharProgress);
                elements.modalPostContent.style.height = 'auto';
                closeCreatePostModal();

                // Refresh feed
                refreshFeed();
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao criar post', 'error');
            }
        } catch (error) {
            console.error('Erro criando post:', error);
            showToast('Erro de conexão', 'error');
        } finally {
            // Reabilitar botão
            elements.modalPostBtn.disabled = elements.modalPostContent.value.trim().length === 0;
            elements.modalPostBtn.textContent = 'Postar';
        }
    }

    /**
     * Carrega posts do feed
     */
    async function loadFeed(append = false) {
        if (state.isLoading) return;

        state.isLoading = true;

        if (!append) {
            elements.feedPosts.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Carregando posts...</p></div>';
            state.offset = 0;
        }

        try {
            const response = await fetch(`/api/feed/posts?limit=${config.postsPerPage}&offset=${state.offset}&tab=${state.currentTab}`);

            if (response.ok) {
                const data = await response.json();
                console.log('Feed loaded:', data.posts.length, 'posts');

                if (!append) {
                    state.posts = data.posts;
                    elements.feedPosts.innerHTML = '';
                } else {
                    state.posts = [...state.posts, ...data.posts];
                }

                if (state.posts.length === 0) {
                    elements.feedPosts.innerHTML = `
                        <div class="empty-feed">
                            <div class="empty-feed-icon">📝</div>
                            <h3>Nenhum post encontrado</h3>
                            <p>Seja o primeiro a postar algo!</p>
                        </div>
                    `;
                } else {
                    if (append) {
                        data.posts.forEach(post => {
                            elements.feedPosts.appendChild(createPostElement(post));
                        });
                    } else {
                        state.posts.forEach(post => {
                            elements.feedPosts.appendChild(createPostElement(post));
                        });
                    }

                    // Show/hide load more button
                    if (elements.loadMoreContainer) {
                        elements.loadMoreContainer.style.display = data.posts.length === config.postsPerPage ? 'block' : 'none';
                    }
                }

                state.offset += data.posts.length;
            } else {
                console.error('Failed to load feed:', response.status, response.statusText);
                elements.feedPosts.innerHTML = '<div class="empty-feed"><p>Erro ao carregar posts</p></div>';
            }
        } catch (error) {
            console.error('Erro carregando feed:', error);
            elements.feedPosts.innerHTML = '<div class="empty-feed"><p>Erro de conexão</p></div>';
        } finally {
            state.isLoading = false;
        }
    }

    /**
     * Cria elemento HTML do post
     */
    function createPostElement(post) {
        const postElement = document.createElement('div');
        postElement.className = 'feed-post';
        postElement.dataset.postId = post.id;

        // Indicador de retweet se aplicável
        const retweetIndicator = post.retweet_info ?
            `<div class="retweet-indicator">
                <span class="icon">🔄</span>
                <span>${escapeHtml(post.retweet_info.retweeter_username)} republicou</span>
            </div>` : '';

        // Post citado se aplicável
        const quotedPost = post.quoted_post ?
            `<div class="quoted-post">
                <div class="post-header">
                    <div class="user-avatar">👤</div>
                    <div class="post-author">
                        <span class="post-author-name">${escapeHtml(post.quoted_post.author_username)}</span>
                        <span class="post-time">${formatTime(post.quoted_post.timestamp)}</span>
                    </div>
                </div>
                <div class="post-content">${formatPostContent(post.quoted_post.content)}</div>
            </div>` : '';

        postElement.innerHTML = `
            ${retweetIndicator}
            <div class="post-header">
                <div class="user-avatar">👤</div>
                <div class="post-author">
                    <span class="post-author-name">${escapeHtml(post.author_username)}</span>
                    <span class="post-time">${formatTime(post.timestamp)}</span>
                </div>
                <button class="post-actions-menu" onclick="DECTERUM.Feed.showPostMenu('${post.id}', event)">
                    ⋯
                </button>
            </div>

            <div class="post-content-area" onclick="DECTERUM.Feed.openPostModal('${post.id}')">
                <div class="post-content">${formatPostContent(post.content)}</div>
                ${quotedPost}
            </div>

            <!-- Sistema de Votos (Reddit-style) -->
            <div class="post-voting">
                <button class="vote-btn ${post.user_vote === 'up' ? 'voted' : ''}"
                        onclick="event.stopPropagation(); DECTERUM.Feed.votePost('${post.id}', 'up')">
                    ↑ ${post.upvotes || 0}
                </button>
                <div class="vote-score">${post.net_votes || 0}</div>
                <button class="vote-btn ${post.user_vote === 'down' ? 'voted' : ''}"
                        onclick="event.stopPropagation(); DECTERUM.Feed.votePost('${post.id}', 'down')">
                    ↓ ${post.downvotes || 0}
                </button>
            </div>

            <!-- Selos Comunitários -->
            <div class="post-badges" id="badges-${post.id}">
                ${post.badges ? Object.entries(post.badges).map(([type, data]) => `
                    <span class="post-badge">
                        <span class="badge-icon">${getBadgeIcon(type)}</span>
                        <span class="badge-count">${data.count}</span>
                    </span>
                `).join('') : ''}
            </div>

            <div class="post-actions">
                <div class="post-secondary-actions">
                    <button class="action-btn" onclick="event.stopPropagation(); DECTERUM.Feed.openPostModal('${post.id}')">
                        💬
                        <span class="count">${post.comments_count || 0}</span>
                    </button>
                    <button class="action-btn retweet-btn ${post.user_retweeted ? 'retweeted' : ''}"
                            onclick="event.stopPropagation(); DECTERUM.Feed.showRetweetModal('${post.id}')">
                        🔄
                        <span class="count">${post.retweets_count || 0}</span>
                    </button>
                    <button class="action-btn"
                            onclick="event.stopPropagation(); DECTERUM.Feed.showBadgeModal('${post.id}')">
                        🏆
                    </button>
                    <button class="action-btn"
                            onclick="event.stopPropagation(); DECTERUM.Feed.sharePost('${post.id}')">
                        📤
                    </button>
                </div>
            </div>
        `;

        return postElement;
    }


    /**
     * Atualiza votos do post na UI
     */
    function updatePostVotes(postId, postData, userVote) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (!postElement) return;

        const upBtn = postElement.querySelector('.vote-btn:first-of-type');
        const downBtn = postElement.querySelector('.vote-btn:last-of-type');
        const scoreElement = postElement.querySelector('.vote-score');

        // Update button states
        upBtn.className = `vote-btn ${userVote === 'up' ? 'voted' : ''}`;
        downBtn.className = `vote-btn ${userVote === 'down' ? 'voted' : ''}`;

        // Update counts
        upBtn.innerHTML = `↑ ${postData.upvotes}`;
        downBtn.innerHTML = `↓ ${postData.downvotes}`;
        scoreElement.textContent = postData.net_votes;
    }

    /**
     * Mostra modal de selos
     */
    function showBadgeModal(postId) {
        state.currentPostId = postId;
        const modal = document.getElementById('badge-modal');
        modal.style.display = 'flex';
    }

    /**
     * Atribui selo a um post
     */
    async function awardBadge(badgeType) {
        if (!state.currentPostId) return;

        try {
            const response = await fetch(`/api/feed/posts/${state.currentPostId}/badges`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ badge_type: badgeType })
            });

            if (response.ok) {
                const data = await response.json();
                showToast(data.message);
                hideBadgeModal();
                updatePostBadges(state.currentPostId, data.badges);
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao atribuir selo', 'error');
            }
        } catch (error) {
            console.error('Erro atribuindo selo:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    /**
     * Atualiza selos do post na UI
     */
    function updatePostBadges(postId, badges) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (!postElement) return;

        let badgesContainer = postElement.querySelector('.post-badges');
        if (!badgesContainer) {
            badgesContainer = document.createElement('div');
            badgesContainer.className = 'post-badges';
            const postContent = postElement.querySelector('.post-content');
            postContent.after(badgesContainer);
        }

        badgesContainer.innerHTML = Object.entries(badges).map(([type, data]) => `
            <span class="post-badge">
                <span class="badge-icon">${getBadgeIcon(type)}</span>
                <span class="badge-count">${data.count}</span>
            </span>
        `).join('');
    }

    /**
     * Mostra modal de comentários
     */
    async function showCommentsModal(postId) {
        state.currentPostId = postId;
        const modal = document.getElementById('comments-modal');

        elements.commentsList.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Carregando comentários...</p></div>';
        modal.style.display = 'flex';

        try {
            const response = await fetch(`/api/feed/posts/${postId}/comments`);
            if (response.ok) {
                const data = await response.json();
                displayComments(data.comments);
            } else {
                elements.commentsList.innerHTML = '<p>Erro ao carregar comentários</p>';
            }
        } catch (error) {
            console.error('Erro carregando comentários:', error);
            elements.commentsList.innerHTML = '<p>Erro de conexão</p>';
        }
    }

    /**
     * Exibe comentários
     */
    function displayComments(comments) {
        if (comments.length === 0) {
            elements.commentsList.innerHTML = '<p>Nenhum comentário ainda. Seja o primeiro!</p>';
            return;
        }

        elements.commentsList.innerHTML = comments.map(comment => `
            <div class="comment-item" data-comment-id="${comment.id}">
                <div class="comment-avatar">👤</div>
                <div class="comment-content">
                    <div class="comment-author">${escapeHtml(comment.author_username)}</div>
                    <div class="comment-text">${escapeHtml(comment.content).replace(/\n/g, '<br>')}</div>
                    <div class="comment-actions">
                        <div class="post-votes">
                            <button class="vote-btn ${comment.user_vote === 'up' ? 'voted' : ''}"
                                    onclick="DECTERUM.Feed.votePost('${comment.id}', 'up')">
                                ↑ ${comment.upvotes}
                            </button>
                            <div class="vote-score">${comment.net_votes}</div>
                            <button class="vote-btn ${comment.user_vote === 'down' ? 'voted' : ''}"
                                    onclick="DECTERUM.Feed.votePost('${comment.id}', 'down')">
                                ↓ ${comment.downvotes}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Envia comentário
     */
    async function submitComment() {
        const content = elements.commentContent.value.trim();
        if (!content || !state.currentPostId) return;

        try {
            const response = await fetch('/api/feed/posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    parent_post_id: state.currentPostId
                })
            });

            if (response.ok) {
                elements.commentContent.value = '';
                elements.commentCharCount.textContent = '0/500';
                elements.commentBtn.disabled = true;

                showToast('Comentário adicionado!');
                showCommentsModal(state.currentPostId); // Reload comments
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao comentar', 'error');
            }
        } catch (error) {
            console.error('Erro enviando comentário:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    /**
     * Mostra modal de sub-thread
     */
    function showSubThreadModal(postId) {
        state.currentPostId = postId;
        document.getElementById('subthread-modal').style.display = 'flex';
    }

    /**
     * Cria sub-thread
     */
    async function createSubThread(event) {
        event.preventDefault();

        const title = document.getElementById('subthread-title').value.trim();
        const description = document.getElementById('subthread-description').value.trim();

        if (!title || !state.currentPostId) return;

        try {
            const response = await fetch(`/api/feed/posts/${state.currentPostId}/threads`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    description: description
                })
            });

            if (response.ok) {
                const data = await response.json();
                showToast('Sub-thread criada com sucesso!');
                hideSubThreadModal();

                // Clear form
                document.getElementById('subthread-title').value = '';
                document.getElementById('subthread-description').value = '';
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao criar sub-thread', 'error');
            }
        } catch (error) {
            console.error('Erro criando sub-thread:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    /**
     * Troca aba do feed
     */
    function switchTab(tab) {
        state.currentTab = tab;

        // Update UI
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

        // Reload feed
        loadFeed(false);
    }

    /**
     * Atualiza feed
     */
    function refreshFeed() {
        loadFeed(false);
    }

    /**
     * Carrega mais posts
     */
    function loadMorePosts() {
        loadFeed(true);
    }

    // === FUNCIONALIDADES DE REPUBLICAR ===

    /**
     * Mostra modal de retweet
     */
    function showRetweetModal(postId) {
        state.currentPostId = postId;
        document.getElementById('retweet-modal').style.display = 'flex';
    }

    /**
     * Esconde modal de retweet
     */
    function hideRetweetModal() {
        document.getElementById('retweet-modal').style.display = 'none';
        state.currentPostId = null;
    }

    /**
     * Executa retweet
     */
    async function retweet(type) {
        if (!state.currentPostId) return;

        if (type === 'simple') {
            try {
                const response = await fetch(`/api/feed/posts/${state.currentPostId}/retweet`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ type: 'simple' })
                });

                if (response.ok) {
                    const data = await response.json();
                    showToast('Post republicado!');
                    hideRetweetModal();
                    updatePostRetweetCount(state.currentPostId, data.retweets_count, true);
                } else {
                    const error = await response.json();
                    showToast(error.error || 'Erro ao republicar', 'error');
                }
            } catch (error) {
                console.error('Erro republicando:', error);
                showToast('Erro de conexão', 'error');
            }
        } else if (type === 'quote') {
            hideRetweetModal();
            showQuoteRetweetModal();
        }
    }

    /**
     * Mostra modal de quote retweet
     */
    function showQuoteRetweetModal() {
        if (!state.currentPostId) return;

        // Encontrar o post original
        const originalPost = state.posts.find(p => p.id === state.currentPostId);
        if (!originalPost) return;

        // Preencher preview do post
        elements.quotedPostPreview.innerHTML = `
            <div class="post-header">
                <div class="user-avatar">👤</div>
                <div class="post-author">
                    <span class="post-author-name">${escapeHtml(originalPost.author_username)}</span>
                    <span class="post-time">${formatTime(originalPost.timestamp)}</span>
                </div>
            </div>
            <div class="post-content">${formatPostContent(originalPost.content)}</div>
        `;

        document.getElementById('quote-retweet-modal').style.display = 'flex';
        elements.quoteContent.focus();
    }

    /**
     * Esconde modal de quote retweet
     */
    function hideQuoteRetweetModal() {
        document.getElementById('quote-retweet-modal').style.display = 'none';
        elements.quoteContent.value = '';
        elements.quoteCharCount.textContent = '280';
        state.currentPostId = null;
    }

    /**
     * Submete quote retweet
     */
    async function submitQuoteRetweet() {
        const content = elements.quoteContent.value.trim();
        if (!state.currentPostId) return;

        try {
            const response = await fetch(`/api/feed/posts/${state.currentPostId}/retweet`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: 'quote',
                    content: content
                })
            });

            if (response.ok) {
                const data = await response.json();
                showToast('Post republicado com comentário!');
                hideQuoteRetweetModal();
                refreshFeed();
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao republicar', 'error');
            }
        } catch (error) {
            console.error('Erro republicando:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    /**
     * Votar em post (upvote/downvote)
     */
    async function votePost(postId, voteType) {
        try {
            const response = await fetch(`/api/feed/posts/${postId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ vote_type: voteType })
            });

            if (response.ok) {
                const data = await response.json();
                updatePostVotes(postId, data.post, data.user_vote);
                showToast(`${voteType === 'up' ? 'Upvote' : 'Downvote'} registrado!`);
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao votar', 'error');
            }
        } catch (error) {
            console.error('Erro votando:', error);
            // Fallback: simular voto localmente
            simulateVote(postId, voteType);
            showToast('Voto registrado localmente');
        }
    }

    /**
     * Simular voto quando API não está disponível
     */
    function simulateVote(postId, voteType) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (!postElement) return;

        const upBtn = postElement.querySelector('.vote-btn:first-of-type');
        const downBtn = postElement.querySelector('.vote-btn:last-of-type');
        const scoreElement = postElement.querySelector('.vote-score');

        if (!upBtn || !downBtn || !scoreElement) return;

        // Remover classes existentes
        upBtn.classList.remove('voted');
        downBtn.classList.remove('voted');

        // Adicionar classe no botão correspondente
        if (voteType === 'up') {
            upBtn.classList.add('voted');
        } else {
            downBtn.classList.add('voted');
        }

        // Simular mudança na pontuação
        const currentScore = parseInt(scoreElement.textContent) || 0;
        const newScore = voteType === 'up' ? currentScore + 1 : currentScore - 1;
        scoreElement.textContent = newScore;
    }

    /**
     * Atualizar votos do post na UI
     */
    function updatePostVotes(postId, postData, userVote) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (!postElement) return;

        const upBtn = postElement.querySelector('.vote-btn:first-of-type');
        const downBtn = postElement.querySelector('.vote-btn:last-of-type');
        const scoreElement = postElement.querySelector('.vote-score');

        if (upBtn && downBtn && scoreElement) {
            // Update button states
            upBtn.className = `vote-btn ${userVote === 'up' ? 'voted' : ''}`;
            downBtn.className = `vote-btn ${userVote === 'down' ? 'voted' : ''}`;

            // Update counts
            upBtn.innerHTML = `↑ ${postData.upvotes}`;
            downBtn.innerHTML = `↓ ${postData.downvotes}`;
            scoreElement.textContent = postData.net_votes;
        }
    }



    /**
     * Compartilhar post
     */
    async function sharePost(postId) {
        try {
            const postUrl = `${window.location.origin}#post=${postId}`;

            if (navigator.share) {
                await navigator.share({
                    title: 'Post do DECTERUM',
                    url: postUrl
                });
            } else {
                await navigator.clipboard.writeText(postUrl);
                showToast('Link copiado!');
            }
        } catch (error) {
            console.error('Erro compartilhando:', error);
        }
    }

    // === FUNÇÕES AUXILIARES ===

    /**
     * Formatar conteúdo do post (hashtags, mentions, etc)
     */
    function formatPostContent(content) {
        return escapeHtml(content)
            .replace(/\n/g, '<br>')
            .replace(/#(\w+)/g, '<a href="#hashtag/$1" class="hashtag">#$1</a>')
            .replace(/@(\w+)/g, '<a href="#user/$1" class="mention">@$1</a>');
    }

    /**
     * Atualizar contador de caracteres com progress ring
     */
    function updateCharCounter(length, maxLength, countElement, progressElement) {
        const remaining = maxLength - length;
        const percentage = (length / maxLength) * 100;

        if (countElement) {
            countElement.textContent = remaining;
            countElement.style.color = remaining < 20 ? '#ff6b6b' : remaining < 50 ? '#ffa500' : '';
        }

        if (progressElement) {
            const color = remaining < 20 ? '#ff6b6b' : remaining < 50 ? '#ffa500' : 'var(--accent)';
            progressElement.style.background = `conic-gradient(${color} ${percentage * 3.6}deg, var(--border) 0deg)`;
            progressElement.style.display = length > 0 ? 'block' : 'none';
        }
    }

    /**
     * Atualizar contador de retweets
     */
    function updatePostRetweetCount(postId, newCount, userRetweeted) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (!postElement) return;

        const retweetBtn = postElement.querySelector('.retweet-btn');
        const countElement = retweetBtn?.querySelector('.count');

        if (retweetBtn) {
            retweetBtn.classList.toggle('retweeted', userRetweeted);
        }
        if (countElement) {
            countElement.textContent = newCount;
        }
    }


    /**
     * Configurar scroll infinito
     */
    function setupInfiniteScroll() {
        let isLoading = false;

        window.addEventListener('scroll', () => {
            if (isLoading || state.isLoading) return;

            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;

            if (scrollTop + clientHeight >= scrollHeight - 1000) {
                isLoading = true;
                loadFeed(true).finally(() => {
                    isLoading = false;
                });
            }
        });
    }

    /**
     * Mostrar menu de ações do post
     */
    function showPostMenu(postId, event) {
        event.stopPropagation();
        const menu = document.getElementById('post-actions-menu');

        menu.style.display = 'block';
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';

        // Fechar ao clicar fora
        setTimeout(() => {
            document.addEventListener('click', function hideMenu() {
                menu.style.display = 'none';
                document.removeEventListener('click', hideMenu);
            });
        }, 10);
    }

    function formatTime(timestamp) {
        const date = new Date(timestamp * 1000);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'agora';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}d`;

        return date.toLocaleDateString('pt-BR');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Obtém ícone do selo
     */
    function getBadgeIcon(badgeType) {
        const badges = {
            'helpful': '🤝',
            'informative': '📚',
            'funny': '😄',
            'insightful': '💡',
            'accurate': '✅',
            'well_written': '✍️',
            'controversial': '⚡',
            'creative': '🎨'
        };
        return badges[badgeType] || '🏆';
    }

    /**
     * Abre modal do post com comentários
     */
    function openPostModal(postId) {
        const post = state.posts.find(p => p.id === postId);
        if (!post) return;

        // Criar modal dinâmico
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'post-detail-modal';
        modal.style.display = 'flex';

        modal.innerHTML = `
            <div class="modal-content modal-large post-detail-content">
                <div class="modal-header">
                    <div class="modal-title">Post</div>
                    <button class="modal-close" onclick="DECTERUM.Feed.closePostModal()">×</button>
                </div>
                <div class="modal-body post-detail-body">
                    <div class="main-post">
                        ${createPostElement(post).innerHTML}
                    </div>
                    <div class="comment-form">
                        <textarea id="reply-content" placeholder="Escreva uma resposta..." rows="3"></textarea>
                        <div class="comment-actions">
                            <span id="reply-char-count">0/280</span>
                            <button class="btn btn-primary" onclick="DECTERUM.Feed.submitReply('${postId}')" id="reply-btn" disabled>
                                Responder
                            </button>
                        </div>
                    </div>
                    <div class="comments-section">
                        <div class="comments-list" id="post-comments-list">
                            <div class="loading-state">
                                <div class="loading-spinner"></div>
                                <p>Carregando comentários...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Carregar comentários
        loadPostComments(postId);

        // Configurar textarea
        const replyTextarea = document.getElementById('reply-content');
        const replyBtn = document.getElementById('reply-btn');
        const charCount = document.getElementById('reply-char-count');

        replyTextarea.addEventListener('input', function() {
            const length = this.value.length;
            charCount.textContent = `${length}/280`;
            replyBtn.disabled = length === 0 || length > 280;
        });
    }

    /**
     * Fecha modal do post
     */
    function closePostModal() {
        const modal = document.getElementById('post-detail-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Carrega comentários do post
     */
    async function loadPostComments(postId) {
        const commentsList = document.getElementById('post-comments-list');
        if (!commentsList) return;

        try {
            const response = await fetch(`/api/feed/posts/${postId}/comments`);
            if (response.ok) {
                const data = await response.json();
                displayPostComments(data.comments);
            } else {
                commentsList.innerHTML = '<p>Erro ao carregar comentários</p>';
            }
        } catch (error) {
            console.error('Erro carregando comentários:', error);
            commentsList.innerHTML = '<p>Erro de conexão</p>';
        }
    }

    /**
     * Exibe comentários do post
     */
    function displayPostComments(comments) {
        const commentsList = document.getElementById('post-comments-list');
        if (!commentsList) return;

        if (comments.length === 0) {
            commentsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: var(--spacing-4);">Nenhum comentário ainda. Seja o primeiro!</p>';
            return;
        }

        commentsList.innerHTML = comments.map(comment => `
            <div class="comment-item" data-comment-id="${comment.id}">
                <div class="comment-avatar">👤</div>
                <div class="comment-content">
                    <div class="comment-header">
                        <span class="comment-author">${escapeHtml(comment.author_username)}</span>
                        <span class="comment-time">${formatTime(comment.timestamp)}</span>
                    </div>
                    <div class="comment-text">${escapeHtml(comment.content).replace(/\n/g, '<br>')}</div>
                    <div class="comment-actions">
                        <div class="post-voting comment-voting">
                            <button class="vote-btn ${comment.user_vote === 'up' ? 'voted' : ''}"
                                    onclick="DECTERUM.Feed.votePost('${comment.id}', 'up')">
                                ↑ ${comment.upvotes || 0}
                            </button>
                            <div class="vote-score">${comment.net_votes || 0}</div>
                            <button class="vote-btn ${comment.user_vote === 'down' ? 'voted' : ''}"
                                    onclick="DECTERUM.Feed.votePost('${comment.id}', 'down')">
                                ↓ ${comment.downvotes || 0}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Submete resposta ao post
     */
    async function submitReply(postId) {
        const content = document.getElementById('reply-content').value.trim();
        if (!content) return;

        try {
            const response = await fetch('/api/feed/posts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    parent_post_id: postId
                })
            });

            if (response.ok) {
                document.getElementById('reply-content').value = '';
                document.getElementById('reply-char-count').textContent = '0/280';
                document.getElementById('reply-btn').disabled = true;

                showToast('Resposta adicionada!');
                loadPostComments(postId); // Recarregar comentários
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao responder', 'error');
            }
        } catch (error) {
            console.error('Erro enviando resposta:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    function showToast(message, type = 'success') {
        if (window.DECTERUM && window.DECTERUM.showToast) {
            window.DECTERUM.showToast(message, type);
        } else {
            console.log(message);
        }
    }

    // Funções para modais
    function hideBadgeModal() {
        document.getElementById('badge-modal').style.display = 'none';
        state.currentPostId = null;
    }

    function hideCommentsModal() {
        document.getElementById('comments-modal').style.display = 'none';
        state.currentPostId = null;
    }

    function hideSubThreadModal() {
        document.getElementById('subthread-modal').style.display = 'none';
        state.currentPostId = null;
    }

    // === FUNCIONALIDADES DO FAB ===

    /**
     * Alternar menu FAB
     */
    function toggleFabMenu() {
        const isActive = elements.fabMenu.classList.contains('active');

        if (isActive) {
            closeFabMenu();
        } else {
            openFabMenu();
        }
    }

    function openFabMenu() {
        elements.fabMenu.classList.add('active');
        elements.fabMain.classList.add('active');
        elements.fabIcon.textContent = '✕';
    }

    function closeFabMenu() {
        elements.fabMenu.classList.remove('active');
        elements.fabMain.classList.remove('active');
        elements.fabIcon.textContent = '✍️';
    }

    /**
     * Abrir modal de criação de post
     */
    function openCreatePostModal() {
        document.getElementById('create-post-modal').style.display = 'flex';
        elements.modalPostContent.focus();
        closeFabMenu();
    }

    function closeCreatePostModal() {
        document.getElementById('create-post-modal').style.display = 'none';
        elements.modalPostContent.value = '';
        updateCharCounter(0, config.maxPostLength, elements.modalCharCount, elements.modalCharProgress);
    }

    /**
     * Abrir modal de perfil
     */
    function openProfileModal() {
        document.getElementById('profile-modal').style.display = 'flex';
        loadUserProfile();
        closeFabMenu();
    }

    function closeProfileModal() {
        document.getElementById('profile-modal').style.display = 'none';
    }

    async function loadUserProfile() {
        if (!state.currentUser) return;

        try {
            const response = await fetch(`/api/feed/users/${state.currentUser.user_id}/posts`);
            if (response.ok) {
                const data = await response.json();
                displayUserPosts(data.posts);
            } else {
                // Fallback: mostrar posts do usuário atual do feed
                console.log('API de perfil não disponível, usando posts do feed');
                const userPosts = state.posts.filter(post =>
                    post.author_username === state.currentUser.username
                );
                displayUserPosts(userPosts);
            }
        } catch (error) {
            console.error('Erro carregando perfil:', error);
            // Fallback: mostrar posts do usuário atual do feed
            const userPosts = state.posts.filter(post =>
                post.author_username === state.currentUser.username
            );
            displayUserPosts(userPosts);
        }
    }

    function displayUserPosts(posts) {
        if (!elements.profilePosts) return;

        elements.profilePosts.innerHTML = '';

        if (posts.length === 0) {
            elements.profilePosts.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: var(--spacing-4);">Nenhum post ainda</p>';
            return;
        }

        posts.forEach(post => {
            const postElement = createPostElement(post);
            postElement.style.border = 'none';
            postElement.style.borderBottom = '1px solid var(--border)';
            elements.profilePosts.appendChild(postElement);
        });
    }

    function switchProfileTab(tab) {
        document.querySelectorAll('.profile-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        // TODO: Implementar carregamento específico por aba
    }

    /**
     * Abrir modal de pesquisa
     */
    function openSearchModal() {
        document.getElementById('search-modal').style.display = 'flex';
        elements.searchInput.focus();
        closeFabMenu();
    }

    function closeSearchModal() {
        document.getElementById('search-modal').style.display = 'none';
        elements.searchInput.value = '';
        elements.searchResults.innerHTML = `
            <div class="search-placeholder">
                <div class="search-placeholder-icon">🔍</div>
                <p>Digite algo para pesquisar</p>
            </div>
        `;
    }

    async function performSearch() {
        const query = elements.searchInput.value.trim();
        if (!query) return;

        elements.searchResults.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Pesquisando...</p></div>';

        try {
            const response = await fetch(`/api/feed/search?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                displaySearchResults(data.results);
            } else {
                // Fallback: simular resultados de pesquisa
                console.log('API de pesquisa não disponível, usando fallback');
                simulateSearchResults(query);
            }
        } catch (error) {
            console.error('Erro na pesquisa:', error);
            // Fallback: simular resultados de pesquisa
            simulateSearchResults(query);
        }
    }

    /**
     * Simular resultados de pesquisa
     */
    function simulateSearchResults(query) {
        // Filtrar posts existentes que contenham a query
        const matchingPosts = state.posts.filter(post =>
            post.content.toLowerCase().includes(query.toLowerCase()) ||
            post.author_username.toLowerCase().includes(query.toLowerCase())
        );

        // Simular usuários baseados na query
        const simulatedUsers = [
            { type: 'user', username: query, user_id: 'sim_1' },
            { type: 'user', username: query + '_user', user_id: 'sim_2' }
        ];

        const results = [
            ...matchingPosts.map(post => ({ ...post, type: 'post' })),
            ...simulatedUsers
        ];

        displaySearchResults(results);
    }

    function displaySearchResults(results) {
        if (!results || results.length === 0) {
            elements.searchResults.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Nenhum resultado encontrado</p>';
            return;
        }

        elements.searchResults.innerHTML = '';
        results.forEach(item => {
            if (item.type === 'post') {
                const postElement = createPostElement(item);
                elements.searchResults.appendChild(postElement);
            } else if (item.type === 'user') {
                const userElement = createUserSearchResult(item);
                elements.searchResults.appendChild(userElement);
            }
        });
    }

    function createUserSearchResult(user) {
        const userElement = document.createElement('div');
        userElement.className = 'user-search-result';
        userElement.style.cssText = `
            display: flex;
            align-items: center;
            gap: var(--spacing-3);
            padding: var(--spacing-3);
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: background 0.2s ease;
        `;

        userElement.innerHTML = `
            <div class="user-avatar">👤</div>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(user.username)}</div>
                <div style="color: var(--text-secondary); font-size: var(--font-size-sm);">@${escapeHtml(user.username.toLowerCase())}</div>
            </div>
        `;

        userElement.addEventListener('mouseenter', () => {
            userElement.style.background = 'var(--surface)';
        });
        userElement.addEventListener('mouseleave', () => {
            userElement.style.background = 'transparent';
        });

        return userElement;
    }

    function switchSearchTab(tab) {
        document.querySelectorAll('.search-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        performSearch();
    }

    /**
     * Fechar todos os modais
     */
    function closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    // API pública do módulo
    return {
        init,
        createPostFromModal,
        switchTab,
        showRetweetModal,
        hideRetweetModal,
        retweet,
        showQuoteRetweetModal,
        hideQuoteRetweetModal,
        submitQuoteRetweet,
        sharePost,
        showCommentsModal,
        hideCommentsModal,
        submitComment,
        showPostMenu,
        refreshFeed,
        loadMorePosts,
        // Voting and interactions
        votePost,
        // Post detail modal
        openPostModal,
        closePostModal,
        submitReply,
        // Badge system
        showBadgeModal,
        awardBadge,
        hideBadgeModal,
        // FAB functions
        toggleFabMenu,
        openCreatePostModal,
        closeCreatePostModal,
        openProfileModal,
        closeProfileModal,
        switchProfileTab,
        openSearchModal,
        closeSearchModal,
        performSearch,
        switchSearchTab,
        // Ações de usuário (placeholder)
        followUser: () => showToast('Funcionalidade em desenvolvimento'),
        muteUser: () => showToast('Funcionalidade em desenvolvimento'),
        blockUser: () => showToast('Funcionalidade em desenvolvimento'),
        reportPost: () => showToast('Funcionalidade em desenvolvimento'),
        // Getters para debug
        getState: () => state,
        getConfig: () => config
    };
})();