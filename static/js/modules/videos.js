/**
 * DECTERUM Video Module - YouTube Style
 * Gerencia vídeos, shorts, upload e reprodução
 */

window.VideoModule = {
    // Estado do módulo
    currentView: 'home',
    currentVideoData: null,
    shortsQueue: [],
    currentShortIndex: 0,
    uploadInProgress: false,

    // Configurações
    config: {
        videosPerPage: 20,
        maxFileSize: 10 * 1024 * 1024 * 1024, // 10GB
        supportedFormats: ['video/mp4', 'video/webm', 'video/avi', 'video/mov', 'video/ogg'],
        maxTitleLength: 200,
        maxDescriptionLength: 5000
    },

    // Inicialização
    init() {
        this.setupEventListeners();
        this.loadInitialContent();
        console.log('📹 Módulo de Vídeos inicializado');
    },

    // Configurar event listeners
    setupEventListeners() {
        // Navegação entre views
        document.querySelectorAll('.video-view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });

        // Busca de vídeos
        const searchBtn = document.getElementById('video-search-btn');
        const searchInput = document.getElementById('video-search-input');

        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
        }

        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }

        // Filtros de busca
        document.getElementById('video-type-filter')?.addEventListener('change', () => this.performSearch());
        document.getElementById('video-category-filter')?.addEventListener('change', () => this.performSearch());

        // Filtros de trending
        document.querySelectorAll('.trending-filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.trending-filter-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.loadTrendingVideos(e.currentTarget.dataset.filter);
            });
        });

        // Upload de vídeo
        this.setupUploadEventListeners();

        // Player modal
        this.setupModalEventListeners();

        // Shorts navigation
        document.getElementById('shorts-prev')?.addEventListener('click', () => this.previousShort());
        document.getElementById('shorts-next')?.addEventListener('click', () => this.nextShort());

        // Load more
        document.getElementById('load-more-videos')?.addEventListener('click', () => this.loadMoreVideos());
    },

    // Configurar eventos de upload
    setupUploadEventListeners() {
        const uploadArea = document.getElementById('video-upload-area');
        const fileInput = document.getElementById('video-file-input');
        const thumbnailArea = document.getElementById('thumbnail-upload-area');
        const thumbnailInput = document.getElementById('thumbnail-file-input');
        const uploadForm = document.getElementById('video-upload-form');

        // Upload de vídeo
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
            uploadArea.addEventListener('drop', this.handleFileDrop.bind(this));
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));
        }

        // Upload de thumbnail
        if (thumbnailArea && thumbnailInput) {
            thumbnailArea.addEventListener('click', () => thumbnailInput.click());
            thumbnailInput.addEventListener('change', (e) => this.handleThumbnailSelect(e.target.files[0]));
        }

        // Contadores de caracteres
        document.getElementById('video-title')?.addEventListener('input', this.updateCharCount);
        document.getElementById('video-description')?.addEventListener('input', this.updateCharCount);
        document.getElementById('video-tags')?.addEventListener('input', this.updateTagsPreview);

        // Submit do formulário
        if (uploadForm) {
            uploadForm.addEventListener('submit', this.handleVideoUpload.bind(this));
        }

        // Cancelar upload
        document.getElementById('cancel-upload')?.addEventListener('click', this.cancelUpload.bind(this));
    },

    // Configurar eventos do modal
    setupModalEventListeners() {
        const modal = document.getElementById('video-player-modal');
        const backdrop = document.getElementById('modal-backdrop');
        const closeBtn = document.getElementById('modal-close-btn');

        if (backdrop) {
            backdrop.addEventListener('click', () => this.closeVideoModal());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeVideoModal());
        }

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.style.display !== 'none') {
                this.closeVideoModal();
            }
        });

        // Ações do vídeo
        document.getElementById('modal-like-btn')?.addEventListener('click', () => this.likeVideo('like'));
        document.getElementById('modal-dislike-btn')?.addEventListener('click', () => this.likeVideo('dislike'));
        document.getElementById('modal-share-btn')?.addEventListener('click', () => this.shareVideo());

        // Comentários
        document.getElementById('submit-comment')?.addEventListener('click', () => this.submitComment());
        document.getElementById('cancel-comment')?.addEventListener('click', () => this.cancelComment());
    },

    // Trocar de view
    switchView(viewName) {
        // Atualizar botões
        document.querySelectorAll('.video-view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });

        // Mostrar/esconder views
        document.querySelectorAll('.video-view').forEach(view => {
            view.classList.toggle('active', view.id === `${viewName}-view`);
        });

        this.currentView = viewName;

        // Carregar conteúdo específico da view
        switch (viewName) {
            case 'home':
                this.loadHomeVideos();
                break;
            case 'shorts':
                this.loadShortsQueue();
                break;
            case 'trending':
                this.loadTrendingVideos();
                break;
            case 'upload':
                this.resetUploadForm();
                break;
        }
    },

    // Carregar conteúdo inicial
    async loadInitialContent() {
        this.showLoading(true);
        try {
            await this.loadHomeVideos();
        } catch (error) {
            console.error('Erro carregando conteúdo inicial:', error);
            this.showError('Erro ao carregar vídeos');
        } finally {
            this.showLoading(false);
        }
    },

    // Carregar vídeos da home
    async loadHomeVideos(offset = 0, append = false) {
        try {
            const params = new URLSearchParams({
                limit: this.config.videosPerPage,
                offset: offset,
                sort_by: 'timestamp'
            });

            const response = await fetch(`/api/videos?${params}`);
            let data;

            if (response.ok) {
                data = await response.json();
            } else {
                // Usar dados de demo se API não estiver disponível
                console.log('📹 API não disponível, usando dados de demonstração');
                const demoVideos = window.VideoDemoData ? window.VideoDemoData.sampleVideos : [];
                data = {
                    success: true,
                    videos: demoVideos.slice(offset, offset + this.config.videosPerPage),
                    count: demoVideos.length
                };
            }

            if (data.success) {
                this.renderVideoGrid(data.videos, append);

                // Mostrar/esconder botão "carregar mais"
                const loadMoreBtn = document.getElementById('load-more-videos');
                if (loadMoreBtn) {
                    loadMoreBtn.style.display = data.videos.length === this.config.videosPerPage ? 'block' : 'none';
                }
            } else {
                throw new Error(data.error || 'Erro ao carregar vídeos');
            }
        } catch (error) {
            console.error('Erro carregando vídeos da home:', error);
            // Tentar dados de demo como fallback
            if (window.VideoDemoData) {
                const demoVideos = window.VideoDemoData.sampleVideos;
                this.renderVideoGrid(demoVideos, append);
            } else {
                this.showError('Erro ao carregar vídeos da home');
            }
        }
    },

    // Carregar mais vídeos
    async loadMoreVideos() {
        const grid = document.querySelector('.video-grid');
        const currentCount = grid?.children.length || 0;
        await this.loadHomeVideos(currentCount, true);
    },

    // Carregar fila de shorts
    async loadShortsQueue() {
        try {
            const user = await this.getCurrentUser();

            let data;
            if (user) {
                const response = await fetch(`/api/videos/shorts?user_id=${user.user_id}&limit=50`);
                if (response.ok) {
                    data = await response.json();
                }
            }

            // Usar dados de demo se API não disponível ou usuário não encontrado
            if (!data || !data.success) {
                console.log('📱 Usando shorts de demonstração');
                const demoVideos = window.VideoDemoData ? window.VideoDemoData.sampleVideos : [];
                const shorts = demoVideos.filter(video => video.video_type === 'short');
                data = { success: true, shorts: shorts };
            }

            if (data.success) {
                this.shortsQueue = data.shorts;
                this.currentShortIndex = 0;
                this.renderCurrentShort();
            } else {
                throw new Error(data.error || 'Erro ao carregar shorts');
            }
        } catch (error) {
            console.error('Erro carregando shorts:', error);
            // Fallback para dados de demo
            if (window.VideoDemoData) {
                const demoVideos = window.VideoDemoData.sampleVideos;
                const shorts = demoVideos.filter(video => video.video_type === 'short');
                this.shortsQueue = shorts;
                this.currentShortIndex = 0;
                this.renderCurrentShort();
            } else {
                this.showError('Erro ao carregar shorts');
            }
        }
    },

    // Carregar vídeos em alta
    async loadTrendingVideos(videoType = '') {
        try {
            const params = new URLSearchParams({
                limit: this.config.videosPerPage
            });

            if (videoType) {
                params.append('video_type', videoType);
            }

            const response = await fetch(`/api/videos/trending?${params}`);
            let data;

            if (response.ok) {
                data = await response.json();
            } else {
                // Usar dados de demo se API não estiver disponível
                console.log('🔥 Usando trending de demonstração');
                const demoVideos = window.VideoDemoData ? window.VideoDemoData.sampleVideos : [];
                let trending = [...demoVideos].sort((a, b) => b.views_count - a.views_count);

                if (videoType) {
                    trending = trending.filter(video => video.video_type === videoType);
                }

                data = { success: true, trending: trending.slice(0, this.config.videosPerPage) };
            }

            if (data.success) {
                this.renderTrendingGrid(data.trending);
            } else {
                throw new Error(data.error || 'Erro ao carregar trending');
            }
        } catch (error) {
            console.error('Erro carregando trending:', error);
            // Fallback para dados de demo
            if (window.VideoDemoData) {
                const demoVideos = window.VideoDemoData.sampleVideos;
                let trending = [...demoVideos].sort((a, b) => b.views_count - a.views_count);

                if (videoType) {
                    trending = trending.filter(video => video.video_type === videoType);
                }

                this.renderTrendingGrid(trending.slice(0, this.config.videosPerPage));
            } else {
                this.showError('Erro ao carregar vídeos em alta');
            }
        }
    },

    // Realizar busca
    async performSearch() {
        const searchInput = document.getElementById('video-search-input');
        const typeFilter = document.getElementById('video-type-filter');
        const categoryFilter = document.getElementById('video-category-filter');

        const query = searchInput?.value.trim();
        if (!query) {
            await this.loadHomeVideos();
            return;
        }

        try {
            const params = new URLSearchParams({
                q: query,
                limit: this.config.videosPerPage
            });

            if (typeFilter?.value) {
                params.append('video_type', typeFilter.value);
            }

            if (categoryFilter?.value) {
                params.append('category', categoryFilter.value);
            }

            const response = await fetch(`/api/videos/search?${params}`);
            let data;

            if (response.ok) {
                data = await response.json();
            } else {
                // Usar busca em dados de demo
                console.log('🔍 Usando busca de demonstração');
                const demoVideos = window.VideoDemoData ? window.VideoDemoData.sampleVideos : [];

                let results = demoVideos.filter(video => {
                    const searchInTitle = video.title.toLowerCase().includes(query.toLowerCase());
                    const searchInDescription = video.description.toLowerCase().includes(query.toLowerCase());
                    const searchInTags = video.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()));

                    return searchInTitle || searchInDescription || searchInTags;
                });

                // Aplicar filtros
                if (typeFilter?.value) {
                    results = results.filter(video => video.video_type === typeFilter.value);
                }

                if (categoryFilter?.value) {
                    results = results.filter(video => video.category === categoryFilter.value);
                }

                data = { success: true, results: results.slice(0, this.config.videosPerPage) };
            }

            if (data.success) {
                this.renderVideoGrid(data.results);
            } else {
                throw new Error(data.error || 'Erro na busca');
            }
        } catch (error) {
            console.error('Erro na busca:', error);
            // Fallback para busca em dados de demo
            if (window.VideoDemoData) {
                const demoVideos = window.VideoDemoData.sampleVideos;
                let results = demoVideos.filter(video => {
                    const searchInTitle = video.title.toLowerCase().includes(query.toLowerCase());
                    const searchInDescription = video.description.toLowerCase().includes(query.toLowerCase());
                    const searchInTags = video.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()));

                    return searchInTitle || searchInDescription || searchInTags;
                });

                // Aplicar filtros
                if (typeFilter?.value) {
                    results = results.filter(video => video.video_type === typeFilter.value);
                }

                if (categoryFilter?.value) {
                    results = results.filter(video => video.category === categoryFilter.value);
                }

                this.renderVideoGrid(results.slice(0, this.config.videosPerPage));
            } else {
                this.showError('Erro ao buscar vídeos');
            }
        }
    },

    // Renderizar grid de vídeos
    renderVideoGrid(videos, append = false) {
        const grid = document.querySelector('.video-grid');
        if (!grid) return;

        if (!append) {
            grid.innerHTML = '';
        }

        if (videos.length === 0 && !append) {
            this.showEmptyState();
            return;
        }

        videos.forEach(video => {
            const videoCard = this.createVideoCard(video);
            grid.appendChild(videoCard);
        });
    },

    // Renderizar grid de trending
    renderTrendingGrid(videos) {
        const grid = document.querySelector('.trending-grid');
        if (!grid) return;

        grid.innerHTML = '';

        if (videos.length === 0) {
            grid.innerHTML = '<p class="empty-message">Nenhum vídeo em alta no momento</p>';
            return;
        }

        videos.forEach(video => {
            const videoCard = this.createVideoCard(video);
            grid.appendChild(videoCard);
        });
    },

    // Criar card de vídeo
    createVideoCard(video) {
        const card = document.createElement('div');
        card.className = 'video-card';
        card.addEventListener('click', () => this.openVideoModal(video));

        const thumbnailHtml = video.thumbnail_url
            ? `<img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">`
            : `<div class="video-thumbnail-placeholder">🎬</div>`;

        card.innerHTML = `
            <div class="video-thumbnail">
                ${thumbnailHtml}
                <div class="video-duration">${this.formatDuration(video.duration)}</div>
                ${video.video_type === 'short' ? '<div class="video-type-badge">Short</div>' : ''}
            </div>
            <div class="video-card-content">
                <h3 class="video-card-title">${this.escapeHtml(video.title)}</h3>
                <div class="video-card-author">${this.escapeHtml(video.author_username)}</div>
                <div class="video-card-stats">
                    <span>👁️ ${this.formatNumber(video.views_count)}</span>
                    <span>👍 ${this.formatNumber(video.likes_count)}</span>
                    <span>💬 ${this.formatNumber(video.comments_count)}</span>
                    <span>⏰ ${this.formatTimeAgo(video.timestamp)}</span>
                </div>
            </div>
        `;

        return card;
    },

    // Renderizar short atual
    renderCurrentShort() {
        const shortsPlayer = document.querySelector('.shorts-player');
        if (!shortsPlayer) return;

        if (this.shortsQueue.length === 0) {
            shortsPlayer.innerHTML = `
                <div class="shorts-loading">
                    <div class="empty-icon">📱</div>
                    <p>Nenhum short disponível</p>
                </div>
            `;
            return;
        }

        const currentShort = this.shortsQueue[this.currentShortIndex];
        if (!currentShort) return;

        // Para demonstração, mostrar placeholder ao invés de vídeo real
        shortsPlayer.innerHTML = `
            <div class="shorts-content">
                <div class="shorts-placeholder">
                    <div class="shorts-thumbnail">🎬</div>
                    <div class="shorts-overlay">
                        <button class="shorts-play-btn">▶️</button>
                    </div>
                </div>
                <div class="shorts-info">
                    <h3>${this.escapeHtml(currentShort.title)}</h3>
                    <p>@${this.escapeHtml(currentShort.author_username)}</p>
                    <div class="shorts-stats">
                        <span>👁️ ${this.formatNumber(currentShort.views_count)}</span>
                        <span>👍 ${this.formatNumber(currentShort.likes_count)}</span>
                        <span>💬 ${this.formatNumber(currentShort.comments_count)}</span>
                    </div>
                </div>
            </div>
        `;

        // Registrar visualização
        this.recordVideoView(currentShort.id);
    },

    // Navegação de shorts
    previousShort() {
        if (this.currentShortIndex > 0) {
            this.currentShortIndex--;
            this.renderCurrentShort();
        }
    },

    nextShort() {
        if (this.currentShortIndex < this.shortsQueue.length - 1) {
            this.currentShortIndex++;
            this.renderCurrentShort();
        }
    },

    // Abrir modal do vídeo
    async openVideoModal(video) {
        this.currentVideoData = video;
        const modal = document.getElementById('video-player-modal');

        if (!modal) return;

        // Preencher dados do vídeo
        document.getElementById('modal-video-title').textContent = video.title;
        document.getElementById('modal-video-source').src = video.video_url;
        document.getElementById('modal-author-name').textContent = video.author_username;
        document.getElementById('modal-video-views').textContent = `${this.formatNumber(video.views_count)} visualizações`;
        document.getElementById('modal-video-date').textContent = this.formatTimeAgo(video.timestamp);
        document.getElementById('modal-likes-count').textContent = this.formatNumber(video.likes_count);
        document.getElementById('modal-dislikes-count').textContent = this.formatNumber(video.dislikes_count);
        document.getElementById('modal-video-description').textContent = video.description;
        document.getElementById('modal-comments-count').textContent = this.formatNumber(video.comments_count);

        // Carregar player
        const player = document.getElementById('modal-video-player');
        if (player) {
            player.load();
        }

        // Renderizar tags
        this.renderVideoTags(video.tags);

        // Carregar comentários
        await this.loadVideoComments(video.id);

        // Mostrar modal
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Registrar visualização
        this.recordVideoView(video.id);
    },

    // Fechar modal do vídeo
    closeVideoModal() {
        const modal = document.getElementById('video-player-modal');
        const player = document.getElementById('modal-video-player');

        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }

        if (player) {
            player.pause();
            player.currentTime = 0;
        }

        this.currentVideoData = null;
    },

    // Renderizar tags do vídeo
    renderVideoTags(tags) {
        const tagsContainer = document.getElementById('modal-video-tags');
        if (!tagsContainer || !tags) return;

        tagsContainer.innerHTML = '';
        tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'video-tag';
            tagElement.textContent = `#${tag}`;
            tagsContainer.appendChild(tagElement);
        });
    },

    // Carregar comentários do vídeo
    async loadVideoComments(videoId) {
        try {
            const response = await fetch(`/api/videos/${videoId}/comments`);
            let data;

            if (response.ok) {
                data = await response.json();
            } else {
                // Usar comentários de demo
                console.log('💬 Usando comentários de demonstração');
                const demoComments = window.VideoDemoData ? window.VideoDemoData.getDemoComments(videoId) : [];
                data = { success: true, comments: demoComments };
            }

            if (data.success) {
                this.renderComments(data.comments);
            }
        } catch (error) {
            console.error('Erro carregando comentários:', error);
            // Fallback para comentários de demo
            if (window.VideoDemoData) {
                const demoComments = window.VideoDemoData.getDemoComments(videoId);
                this.renderComments(demoComments);
            }
        }
    },

    // Renderizar comentários
    renderComments(comments) {
        const commentsList = document.getElementById('comments-list');
        if (!commentsList) return;

        commentsList.innerHTML = '';

        comments.forEach(comment => {
            const commentElement = this.createCommentElement(comment);
            commentsList.appendChild(commentElement);
        });
    },

    // Criar elemento de comentário
    createCommentElement(comment) {
        const element = document.createElement('div');
        element.className = 'comment-item';

        element.innerHTML = `
            <div class="comment-avatar">${comment.author_username.charAt(0).toUpperCase()}</div>
            <div class="comment-content">
                <div class="comment-author">${this.escapeHtml(comment.author_username)}</div>
                <div class="comment-text">${this.escapeHtml(comment.content)}</div>
                <div class="comment-meta">
                    <span>${this.formatTimeAgo(comment.timestamp)}</span>
                    <span>👍 ${comment.likes_count}</span>
                    ${comment.is_creator_reply ? '<span class="creator-badge">🎬 Criador</span>' : ''}
                </div>
            </div>
        `;

        return element;
    },

    // Like/dislike vídeo
    async likeVideo(likeType) {
        if (!this.currentVideoData) return;

        try {
            const user = await this.getCurrentUser();
            if (!user) {
                this.showError('Usuário não encontrado');
                return;
            }

            const formData = new FormData();
            formData.append('user_id', user.user_id);
            formData.append('username', user.username);
            formData.append('like_type', likeType);

            const response = await fetch(`/api/videos/${this.currentVideoData.id}/like`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Atualizar UI
                this.updateLikeButtons(likeType);
                this.showSuccess(`${likeType === 'like' ? 'Like' : 'Dislike'} registrado!`);
            } else {
                throw new Error(data.error || 'Erro ao registrar like');
            }
        } catch (error) {
            console.error('Erro no like:', error);
            this.showError('Erro ao registrar like');
        }
    },

    // Atualizar botões de like
    updateLikeButtons(likeType) {
        const likeBtn = document.getElementById('modal-like-btn');
        const dislikeBtn = document.getElementById('modal-dislike-btn');

        if (likeType === 'like') {
            likeBtn?.classList.add('liked');
            dislikeBtn?.classList.remove('liked');
        } else {
            dislikeBtn?.classList.add('liked');
            likeBtn?.classList.remove('liked');
        }
    },

    // Compartilhar vídeo
    async shareVideo() {
        if (!this.currentVideoData) return;

        try {
            const user = await this.getCurrentUser();
            if (!user) return;

            const formData = new FormData();
            formData.append('sharer_id', user.user_id);
            formData.append('sharer_username', user.username);
            formData.append('platform', 'internal');

            const response = await fetch(`/api/videos/${this.currentVideoData.id}/share`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Compartilhamento registrado!');

                // Copiar link para clipboard
                const videoUrl = `${window.location.origin}#video=${this.currentVideoData.id}`;
                await navigator.clipboard.writeText(videoUrl);
                this.showSuccess('Link copiado para a área de transferência!');
            }
        } catch (error) {
            console.error('Erro ao compartilhar:', error);
            this.showError('Erro ao compartilhar vídeo');
        }
    },

    // Submeter comentário
    async submitComment() {
        const commentInput = document.getElementById('comment-input');
        const content = commentInput?.value.trim();

        if (!content || !this.currentVideoData) return;

        try {
            const user = await this.getCurrentUser();
            if (!user) {
                this.showError('Usuário não encontrado');
                return;
            }

            const formData = new FormData();
            formData.append('author_id', user.user_id);
            formData.append('author_username', user.username);
            formData.append('content', content);

            const response = await fetch(`/api/videos/${this.currentVideoData.id}/comment`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                commentInput.value = '';
                this.showSuccess('Comentário adicionado!');
                await this.loadVideoComments(this.currentVideoData.id);
            } else {
                throw new Error(data.error || 'Erro ao adicionar comentário');
            }
        } catch (error) {
            console.error('Erro ao comentar:', error);
            this.showError('Erro ao adicionar comentário');
        }
    },

    // Cancelar comentário
    cancelComment() {
        const commentInput = document.getElementById('comment-input');
        if (commentInput) {
            commentInput.value = '';
        }
    },

    // Registrar visualização
    async recordVideoView(videoId) {
        try {
            const user = await this.getCurrentUser();
            if (!user) return;

            const formData = new FormData();
            formData.append('viewer_id', user.user_id);
            formData.append('viewer_username', user.username);
            formData.append('watch_time', '30'); // Simular 30 segundos
            formData.append('completion_rate', '0.5'); // 50%

            await fetch(`/api/videos/${videoId}/view`, {
                method: 'POST',
                body: formData
            });
        } catch (error) {
            console.error('Erro registrando visualização:', error);
        }
    },

    // === UPLOAD DE VÍDEO ===

    // Resetar formulário de upload
    resetUploadForm() {
        const form = document.getElementById('video-upload-form');
        if (form) {
            form.reset();
        }

        const videoPreview = document.getElementById('video-preview');
        const thumbnailPreview = document.getElementById('thumbnail-preview');
        const uploadProgress = document.getElementById('upload-progress');
        const submitUpload = document.getElementById('submit-upload');

        if (videoPreview) videoPreview.style.display = 'none';
        if (thumbnailPreview) thumbnailPreview.style.display = 'none';
        if (uploadProgress) uploadProgress.style.display = 'none';
        if (submitUpload) submitUpload.disabled = true;

        this.updateCharCount();
        this.updateTagsPreview();
    },

    // Manipular drag over
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    },

    // Manipular drop de arquivo
    handleFileDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFileSelect(files[0]);
        }
    },

    // Manipular seleção de arquivo
    async handleFileSelect(file) {
        if (!file) return;

        // Validar arquivo
        const validation = this.validateVideoFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }

        // Mostrar preview
        await this.showVideoPreview(file);

        // Habilitar botão de envio
        document.getElementById('submit-upload').disabled = false;
    },

    // Validar arquivo de vídeo
    validateVideoFile(file) {
        // Verificar tipo
        if (!this.config.supportedFormats.includes(file.type)) {
            return {
                valid: false,
                error: 'Formato de arquivo não suportado. Use MP4, WebM, AVI, MOV ou OGV.'
            };
        }

        // Verificar tamanho
        if (file.size > this.config.maxFileSize) {
            return {
                valid: false,
                error: 'Arquivo muito grande. Tamanho máximo: 10GB.'
            };
        }

        return { valid: true };
    },

    // Mostrar preview do vídeo
    async showVideoPreview(file) {
        const preview = document.getElementById('video-preview');
        const video = document.getElementById('preview-video');

        if (!preview || !video) return;

        const url = URL.createObjectURL(file);
        video.src = url;

        // Aguardar carregamento dos metadados
        await new Promise((resolve) => {
            video.addEventListener('loadedmetadata', resolve, { once: true });
        });

        // Atualizar informações
        const duration = Math.round(video.duration);
        const size = (file.size / (1024 * 1024)).toFixed(1);
        const type = duration <= 60 ? 'Short' : 'Vídeo Longo';

        document.getElementById('video-duration').textContent = `Duração: ${this.formatDuration(duration)}`;
        document.getElementById('video-size').textContent = `Tamanho: ${size} MB`;
        document.getElementById('video-type-indicator').textContent = `Tipo: ${type}`;

        preview.style.display = 'block';
    },

    // Manipular seleção de thumbnail
    handleThumbnailSelect(file) {
        if (!file || !file.type.startsWith('image/')) {
            this.showError('Selecione uma imagem válida para o thumbnail');
            return;
        }

        const preview = document.getElementById('thumbnail-preview');
        const img = document.getElementById('preview-thumbnail');

        if (preview && img) {
            const url = URL.createObjectURL(file);
            img.src = url;
            preview.style.display = 'block';
        }
    },

    // Atualizar contador de caracteres
    updateCharCount(e) {
        if (e?.target) {
            const input = e.target;
            const countElement = document.getElementById(input.id.replace('video-', '') + '-count');
            if (countElement) {
                countElement.textContent = input.value.length;
            }
        } else {
            // Atualizar todos os contadores
            const titleInput = document.getElementById('video-title');
            const descInput = document.getElementById('video-description');

            if (titleInput) {
                const titleCount = document.getElementById('title-count');
                if (titleCount) {
                    titleCount.textContent = titleInput.value.length;
                }
            }
            if (descInput) {
                const descCount = document.getElementById('description-count');
                if (descCount) {
                    descCount.textContent = descInput.value.length;
                }
            }
        }
    },

    // Atualizar preview de tags
    updateTagsPreview() {
        const tagsInput = document.getElementById('video-tags');
        const preview = document.getElementById('tags-preview');

        if (!tagsInput || !preview) return;

        const tags = tagsInput.value.split(',')
            .map(tag => tag.trim())
            .filter(tag => tag.length > 0);

        preview.innerHTML = '';

        tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag-item';
            const escapedTag = tag.replace(/[&<>"']/g, function(m) {
                return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
            });
            tagElement.innerHTML = `
                ${escapedTag}
                <span class="tag-remove" onclick="VideoModule.removeTag('${escapedTag}')">×</span>
            `;
            preview.appendChild(tagElement);
        });
    },

    // Remover tag
    removeTag(tagToRemove) {
        const tagsInput = document.getElementById('video-tags');
        if (!tagsInput) return;

        const tags = tagsInput.value.split(',')
            .map(tag => tag.trim())
            .filter(tag => tag !== tagToRemove);

        tagsInput.value = tags.join(', ');
        this.updateTagsPreview();
    },

    // Manipular envio do vídeo
    async handleVideoUpload(e) {
        e.preventDefault();

        if (this.uploadInProgress) return;

        const fileInput = document.getElementById('video-file-input');
        const thumbnailInput = document.getElementById('thumbnail-file-input');

        if (!fileInput) {
            this.showError('Elemento de upload não encontrado');
            return;
        }

        if (!fileInput.files || !fileInput.files[0]) {
            this.showError('Selecione um arquivo de vídeo');
            return;
        }

        // Validar campos obrigatórios
        const titleInput = document.getElementById('video-title');
        if (!titleInput) {
            this.showError('Campo de título não encontrado');
            return;
        }

        const title = titleInput.value.trim();
        if (!title) {
            this.showError('Título é obrigatório');
            return;
        }

        this.uploadInProgress = true;
        this.showUploadProgress(true);

        try {
            const user = await this.getCurrentUser();
            if (!user) {
                throw new Error('Usuário não encontrado');
            }

            // Preparar FormData
            const formData = new FormData();
            formData.append('video_file', fileInput.files[0]);
            if (thumbnailInput && thumbnailInput.files && thumbnailInput.files[0]) {
                formData.append('thumbnail_file', thumbnailInput.files[0]);
            }
            formData.append('title', title);

            const descriptionEl = document.getElementById('video-description');
            formData.append('description', descriptionEl ? descriptionEl.value : '');

            const categoryEl = document.getElementById('video-category');
            formData.append('category', categoryEl ? categoryEl.value : 'general');

            const tagsEl = document.getElementById('video-tags');
            formData.append('tags', tagsEl ? tagsEl.value : '');

            const visibilityEl = document.getElementById('video-visibility');
            formData.append('is_public', visibilityEl ? visibilityEl.value === 'public' : true);
            formData.append('author_id', user.user_id);
            formData.append('author_username', user.username);

            // Simular progresso (em produção, usar XMLHttpRequest com progress)
            this.simulateUploadProgress();

            const response = await fetch('/api/videos/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Vídeo enviado com sucesso!');
                this.resetUploadForm();
                this.switchView('home');
                await this.loadHomeVideos(); // Recarregar lista
            } else {
                throw new Error(data.error || 'Erro no upload');
            }

        } catch (error) {
            console.error('Erro no upload:', error);
            this.showError('Erro no upload: ' + error.message);
        } finally {
            this.uploadInProgress = false;
            this.showUploadProgress(false);
        }
    },

    // Cancelar upload
    cancelUpload() {
        if (this.uploadInProgress) {
            // Em produção, cancelar requisição
            this.uploadInProgress = false;
        }
        this.resetUploadForm();
    },

    // Mostrar progresso de upload
    showUploadProgress(show) {
        const progressContainer = document.getElementById('upload-progress');
        const submitBtn = document.getElementById('submit-upload');

        if (progressContainer) {
            progressContainer.style.display = show ? 'block' : 'none';
        }

        if (submitBtn) {
            submitBtn.disabled = show;
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoading = submitBtn.querySelector('.btn-loading');

            if (btnText && btnLoading) {
                btnText.style.display = show ? 'none' : 'inline';
                btnLoading.style.display = show ? 'flex' : 'none';
            }
        }
    },

    // Simular progresso de upload
    simulateUploadProgress() {
        const progressFill = document.getElementById('progress-fill');
        const progressPercentage = document.getElementById('progress-percentage');
        const progressStatus = document.getElementById('progress-status');

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 100) progress = 100;

            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            if (progressPercentage) {
                progressPercentage.textContent = `${Math.round(progress)}%`;
            }
            if (progressStatus) {
                if (progress < 30) {
                    progressStatus.textContent = 'Enviando arquivo...';
                } else if (progress < 70) {
                    progressStatus.textContent = 'Processando vídeo...';
                } else if (progress < 100) {
                    progressStatus.textContent = 'Finalizando...';
                } else {
                    progressStatus.textContent = 'Concluído!';
                }
            }

            if (progress >= 100) {
                clearInterval(interval);
            }
        }, 200);
    },

    // === FUNÇÕES UTILITÁRIAS ===

    // Obter usuário atual
    async getCurrentUser() {
        try {
            const response = await fetch('/api/user');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Erro obtendo usuário:', error);
        }
        return null;
    },

    // Formatar duração
    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        }

        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;

        if (minutes < 60) {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }

        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    // Formatar números
    formatNumber(num) {
        if (num < 1000) return num.toString();
        if (num < 1000000) return (num / 1000).toFixed(1) + 'K';
        return (num / 1000000).toFixed(1) + 'M';
    },

    // Formatar tempo relativo
    formatTimeAgo(timestamp) {
        const now = Date.now() / 1000;
        const diff = now - timestamp;

        if (diff < 60) return 'agora';
        if (diff < 3600) return `${Math.floor(diff / 60)}min atrás`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
        if (diff < 2592000) return `${Math.floor(diff / 86400)}d atrás`;
        return `${Math.floor(diff / 2592000)}mês atrás`;
    },

    // Escapar HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Mostrar loading
    showLoading(show) {
        const loading = document.getElementById('videos-loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    },

    // Mostrar estado vazio
    showEmptyState() {
        const empty = document.getElementById('videos-empty');
        if (empty) {
            empty.style.display = 'flex';
        }
    },

    // Mostrar sucesso
    showSuccess(message) {
        // Implementar notificação de sucesso
        console.log('✅', message);
        alert(message); // Temporário
    },

    // Mostrar erro
    showError(message) {
        // Implementar notificação de erro
        console.error('❌', message);
        alert(message); // Temporário
    }
};

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('videos-section')) {
        VideoModule.init();
    }
});