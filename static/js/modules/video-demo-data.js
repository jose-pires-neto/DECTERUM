/**
 * Dados de demonstração para o módulo de vídeos
 * Este arquivo cria vídeos fictícios para testar a interface
 */

window.VideoDemoData = {
    // Dados de exemplo de vídeos
    sampleVideos: [
        {
            id: "demo-1",
            author_id: "user-1",
            author_username: "TechGuru",
            title: "Introdução ao DECTERUM P2P",
            description: "Aprenda como funciona a rede descentralizada DECTERUM e suas funcionalidades principais.",
            video_url: "/api/videos/demo/intro.mp4",
            thumbnail_url: null,
            duration: 180,
            video_type: "long",
            resolution: "1080p",
            size_bytes: 25000000,
            mime_type: "video/mp4",
            timestamp: Date.now() / 1000 - 3600,
            views_count: 1250,
            likes_count: 89,
            dislikes_count: 3,
            comments_count: 24,
            shares_count: 12,
            is_public: true,
            is_monetized: false,
            tags: ["tutorial", "p2p", "decentralizado"],
            category: "technology",
            language: "pt-BR",
            quality_levels: ["720p", "1080p"],
            chapters: [],
            subtitles_url: null,
            metadata: {}
        },
        {
            id: "demo-2",
            author_id: "user-2",
            author_username: "CodingLife",
            title: "Quick Tip: FastAPI Routes",
            description: "Dica rápida sobre como criar rotas eficientes no FastAPI",
            video_url: "/api/videos/demo/fastapi-tip.mp4",
            thumbnail_url: null,
            duration: 45,
            video_type: "short",
            resolution: "720p",
            size_bytes: 8500000,
            mime_type: "video/mp4",
            timestamp: Date.now() / 1000 - 1800,
            views_count: 856,
            likes_count: 67,
            dislikes_count: 1,
            comments_count: 15,
            shares_count: 8,
            is_public: true,
            is_monetized: false,
            tags: ["fastapi", "python", "tip"],
            category: "tutorial",
            language: "pt-BR",
            quality_levels: ["720p"],
            chapters: [],
            subtitles_url: null,
            metadata: {}
        },
        {
            id: "demo-3",
            author_id: "user-3",
            author_username: "DevMaster",
            title: "Construindo UIs Modernas com CSS Grid",
            description: "Tutorial completo sobre CSS Grid e como criar layouts responsivos modernos para aplicações web.",
            video_url: "/api/videos/demo/css-grid.mp4",
            thumbnail_url: null,
            duration: 892,
            video_type: "long",
            resolution: "1080p",
            size_bytes: 125000000,
            mime_type: "video/mp4",
            timestamp: Date.now() / 1000 - 7200,
            views_count: 2340,
            likes_count: 156,
            dislikes_count: 8,
            comments_count: 45,
            shares_count: 23,
            is_public: true,
            is_monetized: false,
            tags: ["css", "grid", "frontend", "responsive"],
            category: "tutorial",
            language: "pt-BR",
            quality_levels: ["720p", "1080p"],
            chapters: [
                {"time": 0, "title": "Introdução"},
                {"time": 120, "title": "Conceitos Básicos"},
                {"time": 300, "title": "Layouts Práticos"},
                {"time": 600, "title": "Responsividade"},
                {"time": 780, "title": "Conclusão"}
            ],
            subtitles_url: null,
            metadata: {}
        },
        {
            id: "demo-4",
            author_id: "user-4",
            author_username: "QuickHacks",
            title: "JavaScript: Arrow Functions em 30s",
            description: "Entenda arrow functions rapidamente!",
            video_url: "/api/videos/demo/arrow-functions.mp4",
            thumbnail_url: null,
            duration: 30,
            video_type: "short",
            resolution: "720p",
            size_bytes: 5200000,
            mime_type: "video/mp4",
            timestamp: Date.now() / 1000 - 900,
            views_count: 445,
            likes_count: 38,
            dislikes_count: 2,
            comments_count: 9,
            shares_count: 5,
            is_public: true,
            is_monetized: false,
            tags: ["javascript", "es6", "quick"],
            category: "tutorial",
            language: "pt-BR",
            quality_levels: ["720p"],
            chapters: [],
            subtitles_url: null,
            metadata: {}
        },
        {
            id: "demo-5",
            author_id: "user-5",
            author_username: "NetworkGuru",
            title: "Como Funciona uma Rede P2P",
            description: "Explicação detalhada sobre redes peer-to-peer, protocolos, descoberta de nós e comunicação descentralizada.",
            video_url: "/api/videos/demo/p2p-network.mp4",
            thumbnail_url: null,
            duration: 654,
            video_type: "long",
            resolution: "1080p",
            size_bytes: 89000000,
            mime_type: "video/mp4",
            timestamp: Date.now() / 1000 - 14400,
            views_count: 1789,
            likes_count: 123,
            dislikes_count: 5,
            comments_count: 67,
            shares_count: 34,
            is_public: true,
            is_monetized: false,
            tags: ["p2p", "network", "descentralizado", "protocolo"],
            category: "education",
            language: "pt-BR",
            quality_levels: ["720p", "1080p"],
            chapters: [
                {"time": 0, "title": "O que é P2P"},
                {"time": 180, "title": "Protocolos P2P"},
                {"time": 360, "title": "Descoberta de Nós"},
                {"time": 480, "title": "Comunicação Direta"},
                {"time": 580, "title": "Vantagens e Desvantagens"}
            ],
            subtitles_url: null,
            metadata: {}
        }
    ],

    // Comentários de exemplo
    sampleComments: {
        "demo-1": [
            {
                id: "comment-1",
                video_id: "demo-1",
                author_id: "user-6",
                author_username: "Learner123",
                content: "Ótima explicação! Finalmente entendi como funciona o DECTERUM.",
                timestamp: Date.now() / 1000 - 2400,
                parent_comment_id: null,
                likes_count: 5,
                replies_count: 1,
                is_pinned: false,
                is_creator_reply: false
            },
            {
                id: "comment-2",
                video_id: "demo-1",
                author_id: "user-1",
                author_username: "TechGuru",
                content: "Obrigado! Tem mais conteúdo vindo por aí.",
                timestamp: Date.now() / 1000 - 2000,
                parent_comment_id: "comment-1",
                likes_count: 2,
                replies_count: 0,
                is_pinned: false,
                is_creator_reply: true
            }
        ],
        "demo-3": [
            {
                id: "comment-3",
                video_id: "demo-3",
                author_id: "user-7",
                author_username: "CSSFan",
                content: "CSS Grid mudou minha vida! Layouts ficaram muito mais fáceis.",
                timestamp: Date.now() / 1000 - 5400,
                parent_comment_id: null,
                likes_count: 8,
                replies_count: 0,
                is_pinned: false,
                is_creator_reply: false
            }
        ]
    },

    // Injetar dados de demo no sistema
    injectDemoData() {
        // Simular dados carregados para demonstração
        if (window.VideoModule) {
            console.log('📹 Dados de demonstração carregados para módulo de vídeos');
            return this.sampleVideos;
        }
        return [];
    },

    // Obter comentários de demo para um vídeo
    getDemoComments(videoId) {
        return this.sampleComments[videoId] || [];
    }
};