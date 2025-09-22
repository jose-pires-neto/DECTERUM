import uuid
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class Post:
    """Modelo para posts do feed"""
    id: str
    author_id: str
    author_username: str
    content: str
    timestamp: float
    post_type: str = "text"  # text, image, video, link
    parent_post_id: Optional[str] = None  # Para sub-threads
    thread_level: int = 0  # Nível da thread (0 = post principal)
    upvotes: int = 0
    downvotes: int = 0
    comments_count: int = 0
    retweets_count: int = 0
    shares_count: int = 0
    weight_score: float = 1.0  # Score calculado com base no peso dos votos
    is_pinned: bool = False
    tags: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def create(cls, author_id: str, author_username: str, content: str,
               post_type: str = "text", parent_post_id: Optional[str] = None):
        """Cria um novo post"""
        thread_level = 0
        if parent_post_id:
            # Se é uma resposta, determinar o nível da thread
            thread_level = 1  # Será calculado dinamicamente pelo serviço

        return cls(
            id=str(uuid.uuid4()),
            author_id=author_id,
            author_username=author_username,
            content=content,
            timestamp=time.time(),
            post_type=post_type,
            parent_post_id=parent_post_id,
            thread_level=thread_level
        )

    @property
    def formatted_time(self) -> str:
        """Retorna timestamp formatado"""
        return datetime.fromtimestamp(self.timestamp).strftime("%d/%m/%Y %H:%M")

    @property
    def net_votes(self) -> int:
        """Diferença entre upvotes e downvotes"""
        return self.upvotes - self.downvotes


@dataclass
class Vote:
    """Modelo para votos em posts"""
    id: str
    post_id: str
    voter_id: str
    voter_username: str
    vote_type: str  # "up", "down"
    vote_weight: float = 1.0  # Peso do voto baseado na reputação do usuário
    timestamp: float = time.time()

    @classmethod
    def create(cls, post_id: str, voter_id: str, voter_username: str,
               vote_type: str, vote_weight: float = 1.0):
        """Cria um novo voto"""
        return cls(
            id=str(uuid.uuid4()),
            post_id=post_id,
            voter_id=voter_id,
            voter_username=voter_username,
            vote_type=vote_type,
            vote_weight=vote_weight,
            timestamp=time.time()
        )


@dataclass
class CommunityBadge:
    """Modelo para selos comunitários"""
    id: str
    post_id: str
    badge_type: str  # "funny", "informative", "controversial", "helpful", "creative"
    awarded_by: str
    awarded_by_username: str
    timestamp: float = time.time()
    count: int = 1  # Quantas vezes foi atribuído

    @classmethod
    def create(cls, post_id: str, badge_type: str, awarded_by: str, awarded_by_username: str):
        """Cria um novo selo comunitário"""
        return cls(
            id=str(uuid.uuid4()),
            post_id=post_id,
            badge_type=badge_type,
            awarded_by=awarded_by,
            awarded_by_username=awarded_by_username,
            timestamp=time.time()
        )


@dataclass
class UserReputation:
    """Modelo para reputação do usuário"""
    user_id: str
    username: str
    total_posts: int = 0
    total_votes_received: int = 0
    total_votes_given: int = 0
    positive_votes_received: int = 0
    badges_received: int = 0
    engagement_score: float = 1.0  # Score de engajamento
    vote_weight: float = 1.0  # Peso dos votos deste usuário
    reputation_level: str = "novato"  # novato, ativo, experiente, especialista, lenda
    last_updated: float = time.time()

    @property
    def vote_accuracy(self) -> float:
        """Precisão dos votos (votos positivos / total de votos dados)"""
        if self.total_votes_given == 0:
            return 0.5
        # Aqui seria calculado com base no histórico de votos bem-sucedidos
        return min(1.0, self.positive_votes_received / self.total_votes_given)

    def calculate_vote_weight(self) -> float:
        """Calcula o peso do voto baseado na reputação"""
        base_weight = 1.0

        # Bônus por engajamento
        engagement_bonus = min(2.0, self.engagement_score)

        # Bônus por precisão de votos
        accuracy_bonus = self.vote_accuracy * 0.5

        # Bônus por selos recebidos
        badge_bonus = min(1.0, self.badges_received * 0.1)

        # Peso final
        weight = base_weight + engagement_bonus + accuracy_bonus + badge_bonus

        return min(5.0, weight)  # Máximo de 5x

    def update_reputation_level(self):
        """Atualiza o nível de reputação baseado nas métricas"""
        score = self.engagement_score + self.vote_accuracy + (self.badges_received * 0.1)

        if score >= 10:
            self.reputation_level = "lenda"
        elif score >= 5:
            self.reputation_level = "especialista"
        elif score >= 3:
            self.reputation_level = "experiente"
        elif score >= 1.5:
            self.reputation_level = "ativo"
        else:
            self.reputation_level = "novato"


@dataclass
class SubThread:
    """Modelo para sub-threads (ramificações de discussão)"""
    id: str
    root_post_id: str  # Post principal que originou a thread
    parent_thread_id: Optional[str]  # Thread pai (para threads aninhadas)
    title: str
    description: str
    created_by: str
    created_by_username: str
    timestamp: float = time.time()
    posts_count: int = 0
    participants_count: int = 0
    is_active: bool = True

    @classmethod
    def create(cls, root_post_id: str, title: str, description: str,
               created_by: str, created_by_username: str, parent_thread_id: Optional[str] = None):
        """Cria uma nova sub-thread"""
        return cls(
            id=str(uuid.uuid4()),
            root_post_id=root_post_id,
            parent_thread_id=parent_thread_id,
            title=title,
            description=description,
            created_by=created_by,
            created_by_username=created_by_username,
            timestamp=time.time()
        )


# Constantes para tipos de badge
BADGE_TYPES = {
    "funny": "😄 Engraçado",
    "informative": "📚 Informativo",
    "controversial": "🔥 Polêmico",
    "helpful": "🤝 Útil",
    "creative": "🎨 Criativo",
    "insightful": "💡 Perspicaz",
    "well_written": "✍️ Bem Escrito",
    "accurate": "✅ Preciso"
}

# Constantes para tipos de post
POST_TYPES = {
    "text": "Texto",
    "image": "Imagem",
    "video": "Vídeo",
    "link": "Link",
    "poll": "Enquete",
    "announcement": "Anúncio"
}