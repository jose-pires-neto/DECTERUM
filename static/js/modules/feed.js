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
        sort: 'timestamp',
        isLoading: false,
        currentPostId: null,
        availableBadges: {},
        initialized: false
    };

    // Configurações
    const config = {
        postsPerPage: 20,
        maxPostLength: 500,
        maxCommentLength: 500
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
        loadUserReputation();
        loadBadgeTypes();
        loadFeed();

        state.initialized = true;
        console.log('🔥 Feed module initialized');
    }

    /**
     * Cache dos elementos DOM
     */
    function cacheElements() {
        elements = {
            postContent: document.getElementById('post-content'),
            postTags: document.getElementById('post-tags'),
            charCount: document.getElementById('char-count'),
            postBtn: document.getElementById('post-btn'),
            feedPosts: document.getElementById('feed-posts'),
            loadMoreContainer: document.getElementById('load-more-container'),
            commentContent: document.getElementById('comment-content'),
            commentCharCount: document.getElementById('comment-char-count'),
            commentBtn: document.getElementById('comment-btn'),
            feedUsername: document.getElementById('feed-username'),
            feedUserReputation: document.getElementById('feed-user-reputation'),
            badgeGrid: document.getElementById('badge-grid'),
            commentsList: document.getElementById('comments-list')
        };
    }

    /**
     * Configuração dos event listeners
     */
    function setupEventListeners() {
        // Post creation form
        if (elements.postContent) {
            elements.postContent.addEventListener('input', function() {
                const length = this.value.length;
                elements.charCount.textContent = `${length}/${config.maxPostLength}`;
                elements.postBtn.disabled = length === 0 || length > config.maxPostLength;

                // Auto-resize
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 120) + 'px';
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
     * Carrega reputação do usuário
     */
    async function loadUserReputation() {
        try {
            const response = await fetch('/api/feed/me/reputation');
            if (response.ok) {
                const data = await response.json();
                updateUserReputationDisplay(data.reputation);
            } else if (response.status === 404) {
                // Reputação não encontrada, usar valores padrão
                updateUserReputationDisplay({
                    reputation_level: 'novato',
                    vote_weight: 1.0
                });
            }
        } catch (error) {
            console.error('Erro carregando reputação:', error);
            // Usar valores padrão em caso de erro
            updateUserReputationDisplay({
                reputation_level: 'novato',
                vote_weight: 1.0
            });
        }
    }

    /**
     * Atualiza exibição da reputação
     */
    function updateUserReputationDisplay(reputation) {
        if (elements.feedUserReputation && reputation) {
            const levelElement = elements.feedUserReputation.querySelector('.reputation-level');
            const weightElement = elements.feedUserReputation.querySelector('.vote-weight');

            if (levelElement) levelElement.textContent = reputation.reputation_level;
            if (weightElement) weightElement.textContent = `${reputation.vote_weight.toFixed(1)}x`;
        }
    }

    /**
     * Carrega tipos de selos disponíveis
     */
    async function loadBadgeTypes() {
        try {
            const response = await fetch('/api/feed/badge-types');
            if (response.ok) {
                const data = await response.json();
                state.availableBadges = data.badge_types;
            }
        } catch (error) {
            console.error('Erro carregando tipos de selos:', error);
        }
    }

    /**
     * Cria um novo post
     */
    async function createPost() {
        const content = elements.postContent.value.trim();
        const tags = elements.postTags.value.trim();

        if (!content) return;

        try {
            const postData = {
                content: content,
                post_type: 'text',
                tags: tags ? tags.split(',').map(tag => tag.trim()) : []
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
                showToast('Post criado com sucesso!');

                // Clear form
                elements.postContent.value = '';
                elements.postTags.value = '';
                elements.charCount.textContent = '0/500';
                elements.postBtn.disabled = true;

                // Refresh feed
                refreshFeed();
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao criar post', 'error');
            }
        } catch (error) {
            console.error('Erro criando post:', error);
            showToast('Erro de conexão', 'error');
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
            const response = await fetch(`/api/feed/posts?limit=${config.postsPerPage}&offset=${state.offset}&sort_by=${state.sort}`);

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

        const tagsHtml = post.tags.length > 0 ?
            `<div class="post-tags">${post.tags.map(tag => `<span class="post-tag">#${tag}</span>`).join('')}</div>` : '';

        const badgesHtml = Object.keys(post.badges).length > 0 ?
            `<div class="post-badges">${Object.entries(post.badges).map(([type, count]) =>
                `<span class="post-badge">
                    <span class="badge-icon">${getBadgeIcon(type)}</span>
                    <span class="badge-count">${count}</span>
                </span>`
            ).join('')}</div>` : '';

        const commentsPreview = post.comments.length > 0 ?
            `<div class="comments-preview">
                <div class="comments-preview-header">
                    <span class="comments-count">${post.comments_count} comentários</span>
                    <button class="view-all-comments" onclick="DECTERUM.Feed.showCommentsModal('${post.id}')">Ver todos</button>
                </div>
                ${post.comments.slice(0, 2).map(comment =>
                    `<div class="comment-item">
                        <div class="comment-avatar">👤</div>
                        <div class="comment-content">
                            <div class="comment-author">${escapeHtml(comment.author_username)}</div>
                            <div class="comment-text">${escapeHtml(comment.content)}</div>
                        </div>
                    </div>`
                ).join('')}
            </div>` : '';

        postElement.innerHTML = `
            <div class="post-header">
                <div class="user-avatar">👤</div>
                <div class="post-author">
                    <div class="post-author-name">${escapeHtml(post.author_username)}</div>
                    <div class="post-meta">
                        <span class="post-time">${formatTime(post.timestamp)}</span>
                        <div class="reputation-badge">
                            <span class="reputation-level">${post.reputation_level || 'novato'}</span>
                            <span class="vote-weight">${(post.author_vote_weight || 1.0).toFixed(1)}x</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="post-content">${escapeHtml(post.content).replace(/\n/g, '<br>')}</div>

            ${tagsHtml}
            ${badgesHtml}

            <div class="post-actions">
                <div class="post-votes">
                    <button class="vote-btn ${post.user_vote === 'up' ? 'voted' : ''}"
                            onclick="DECTERUM.Feed.votePost('${post.id}', 'up')">
                        ↑ ${post.upvotes}
                    </button>
                    <div class="vote-score">${post.net_votes}</div>
                    <button class="vote-btn ${post.user_vote === 'down' ? 'voted' : ''}"
                            onclick="DECTERUM.Feed.votePost('${post.id}', 'down')">
                        ↓ ${post.downvotes}
                    </button>
                </div>

                <div class="post-secondary-actions">
                    <button class="action-btn" onclick="DECTERUM.Feed.showCommentsModal('${post.id}')">
                        💬 ${post.comments_count}
                    </button>
                    <button class="action-btn" onclick="DECTERUM.Feed.showBadgeModal('${post.id}')">
                        🏆 Selo
                    </button>
                    <button class="action-btn" onclick="DECTERUM.Feed.showSubThreadModal('${post.id}')">
                        🧵 Thread
                    </button>
                </div>
            </div>

            ${commentsPreview}
        `;

        return postElement;
    }

    /**
     * Vota em um post
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
            } else {
                const error = await response.json();
                showToast(error.error || 'Erro ao votar', 'error');
            }
        } catch (error) {
            console.error('Erro votando:', error);
            showToast('Erro de conexão', 'error');
        }
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

        elements.badgeGrid.innerHTML = Object.entries(state.availableBadges).map(([type, name]) => `
            <div class="badge-option" onclick="DECTERUM.Feed.awardBadge('${type}')">
                <div class="badge-option-icon">${getBadgeIcon(type)}</div>
                <div class="badge-option-name">${name}</div>
            </div>
        `).join('');

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
     * Ordena feed
     */
    function sortFeed(sortBy) {
        state.sort = sortBy;

        // Update UI
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-sort="${sortBy}"]`).classList.add('active');

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

    // Funções auxiliares
    function getBadgeIcon(badgeType) {
        const icons = {
            funny: '😄',
            informative: '📚',
            controversial: '🔥',
            helpful: '🤝',
            creative: '🎨',
            insightful: '💡',
            well_written: '✍️',
            accurate: '✅'
        };
        return icons[badgeType] || '🏆';
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

    // API pública do módulo
    return {
        init,
        createPost,
        votePost,
        showBadgeModal,
        hideBadgeModal,
        awardBadge,
        showCommentsModal,
        hideCommentsModal,
        submitComment,
        showSubThreadModal,
        hideSubThreadModal,
        createSubThread,
        sortFeed,
        refreshFeed,
        loadMorePosts,
        // Getters para debug
        getState: () => state,
        getConfig: () => config
    };
})();