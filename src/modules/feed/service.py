import sqlite3
import json
import time
import logging
import threading
from typing import List, Dict, Optional, Tuple
from ..feed.models import Post, Vote, CommunityBadge, UserReputation, SubThread, BADGE_TYPES

logger = logging.getLogger(__name__)


class FeedService:
    """Serviço principal para operações do feed social"""

    def __init__(self, database):
        self.db = database
        self._db_lock = threading.RLock()

    def _get_connection_with_retry(self, max_retries=3):
        """Obtém conexão com retry automático"""
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db.db_path, timeout=60, check_same_thread=False)
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=60000')
                conn.execute('PRAGMA wal_autocheckpoint=100')
                conn.execute('PRAGMA synchronous=NORMAL')
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, tentativa {attempt + 1}/{max_retries}")
                    time.sleep(0.1 * (2 ** attempt))  # Backoff exponencial
                    continue
                raise

    # ========== POSTS ==========

    def create_post(self, author_id: str, author_username: str, content: str,
                   post_type: str = "text", parent_post_id: Optional[str] = None,
                   tags: List[str] = None) -> Post:
        """Cria um novo post"""
        post = Post.create(author_id, author_username, content, post_type, parent_post_id)

        if tags:
            post.tags = tags

        if parent_post_id:
            post.thread_level = self._calculate_thread_level(parent_post_id)

        self._save_post(post)
        self._update_user_stats(author_id, posts_increment=1)

        # Se é um comentário, atualizar contador do post pai
        if parent_post_id:
            self._increment_comments_count(parent_post_id)

        logger.info(f"Post criado: {post.id} por {author_username}")
        return post

    def get_feed(self, user_id: str, limit: int = 50, offset: int = 0,
                sort_by: str = "timestamp") -> List[Dict]:
        """Obtém posts do feed ordenados"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        # Query base para posts principais (não comentários)
        order_clause = {
            "timestamp": "ORDER BY timestamp DESC",
            "weight": "ORDER BY weight_score DESC, timestamp DESC",
            "engagement": "ORDER BY (upvotes + downvotes + comments_count) DESC, timestamp DESC"
        }.get(sort_by, "ORDER BY timestamp DESC")

        cursor.execute(f'''
            SELECT fp.*, ur.reputation_level, ur.vote_weight
            FROM feed_posts fp
            LEFT JOIN user_reputation ur ON fp.author_id = ur.user_id
            WHERE fp.parent_post_id IS NULL
            {order_clause}
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        posts = []
        for row in cursor.fetchall():
            post_data = self._row_to_post_dict(row)

            # Carregar badges do post
            post_data['badges'] = self._get_post_badges(post_data['id'])

            # Carregar comentários principais (3 primeiros)
            post_data['comments'] = self._get_post_comments(post_data['id'], limit=3)

            posts.append(post_data)

        conn.close()
        return posts

    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Busca um post específico"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT fp.*, ur.reputation_level, ur.vote_weight
            FROM feed_posts fp
            LEFT JOIN user_reputation ur ON fp.author_id = ur.user_id
            WHERE fp.id = ?
        ''', (post_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            post_data = self._row_to_post_dict(row)
            post_data['badges'] = self._get_post_badges(post_id)
            post_data['comments'] = self._get_post_comments(post_id)
            return post_data

        return None

    def get_post_comments(self, post_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Obtém comentários de um post"""
        return self._get_post_comments(post_id, limit, offset)

    # ========== VOTAÇÃO ==========

    def vote_post(self, post_id: str, voter_id: str, voter_username: str,
                 vote_type: str) -> bool:
        """Vota em um post (up/down)"""
        if vote_type not in ["up", "down"]:
            return False

        with self._db_lock:
            conn = self._get_connection_with_retry()
            try:
                # Verificar se já votou
                existing_vote = self._get_user_vote_with_conn(conn, post_id, voter_id)

                if existing_vote:
                    if existing_vote['vote_type'] == vote_type:
                        # Remover voto se é o mesmo tipo
                        self._remove_vote_with_conn(conn, existing_vote['id'])
                        logger.info(f"Voto removido: {voter_username} em {post_id}")
                    else:
                        # Atualizar voto para o tipo oposto
                        self._update_vote_with_conn(conn, existing_vote['id'], vote_type)
                        logger.info(f"Voto atualizado: {voter_username} em {post_id}")
                else:
                    # Criar novo voto
                    vote_weight = self._get_user_vote_weight(voter_id)
                    vote = Vote.create(post_id, voter_id, voter_username, vote_type, vote_weight)
                    self._save_vote_with_conn(conn, vote)
                    logger.info(f"Novo voto: {voter_username} ({vote_type}) em {post_id}")

                # Recalcular pontuações do post
                self._recalculate_post_scores_with_conn(conn, post_id)
                self._update_user_stats_with_conn(conn, voter_id, votes_given_increment=1)

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                logger.error(f"Erro votando no post {post_id}: {e}")
                raise
            finally:
                conn.close()

    def get_user_vote(self, post_id: str, user_id: str) -> Optional[str]:
        """Retorna o tipo de voto do usuário no post"""
        vote = self._get_user_vote(post_id, user_id)
        return vote['vote_type'] if vote else None

    # ========== SELOS COMUNITÁRIOS ==========

    def award_badge(self, post_id: str, badge_type: str, awarded_by: str,
                   awarded_by_username: str) -> bool:
        """Atribui um selo comunitário a um post"""
        if badge_type not in BADGE_TYPES:
            return False

        # Verificar se o usuário já deu este selo para este post
        if self._user_has_given_badge(post_id, badge_type, awarded_by):
            return False

        badge = CommunityBadge.create(post_id, badge_type, awarded_by, awarded_by_username)
        self._save_badge(badge)

        # Atualizar estatísticas do autor do post
        post = self.get_post_by_id(post_id)
        if post:
            self._update_user_stats(post['author_id'], badges_increment=1)

        logger.info(f"Selo '{badge_type}' atribuído ao post {post_id} por {awarded_by_username}")
        return True

    def get_post_badges(self, post_id: str) -> Dict[str, int]:
        """Retorna contagem de selos do post"""
        return self._get_post_badges(post_id)

    # ========== SUB-THREADS ==========

    def create_sub_thread(self, root_post_id: str, title: str, description: str,
                         created_by: str, created_by_username: str,
                         parent_thread_id: Optional[str] = None) -> SubThread:
        """Cria uma nova sub-thread"""
        sub_thread = SubThread.create(root_post_id, title, description,
                                    created_by, created_by_username, parent_thread_id)
        self._save_sub_thread(sub_thread)

        logger.info(f"Sub-thread criada: {title} por {created_by_username}")
        return sub_thread

    def get_post_threads(self, post_id: str) -> List[Dict]:
        """Obtém sub-threads de um post"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM sub_threads
            WHERE root_post_id = ? AND is_active = 1
            ORDER BY posts_count DESC, timestamp DESC
        ''', (post_id,))

        threads = []
        for row in cursor.fetchall():
            threads.append({
                'id': row[0],
                'root_post_id': row[1],
                'parent_thread_id': row[2],
                'title': row[3],
                'description': row[4],
                'created_by': row[5],
                'created_by_username': row[6],
                'timestamp': row[7],
                'posts_count': row[8],
                'participants_count': row[9],
                'is_active': bool(row[10])
            })

        conn.close()
        return threads

    # ========== REPUTAÇÃO ==========

    def get_user_reputation(self, user_id: str) -> Optional[UserReputation]:
        """Obtém reputação do usuário"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM user_reputation WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return UserReputation(
                user_id=row[0],
                username=row[1],
                total_posts=row[2],
                total_votes_received=row[3],
                total_votes_given=row[4],
                positive_votes_received=row[5],
                badges_received=row[6],
                engagement_score=row[7],
                vote_weight=row[8],
                reputation_level=row[9],
                last_updated=row[10]
            )
        return None

    def calculate_user_reputation(self, user_id: str):
        """Recalcula reputação do usuário"""
        reputation = self.get_user_reputation(user_id)
        if not reputation:
            # Criar reputação inicial
            user = self.db.get_user(user_id)
            if user:
                reputation = UserReputation(user_id=user_id, username=user['username'])

        if reputation:
            # Recalcular métricas
            stats = self._calculate_user_engagement_stats(user_id)
            reputation.engagement_score = stats['engagement_score']
            reputation.vote_weight = reputation.calculate_vote_weight()
            reputation.update_reputation_level()
            reputation.last_updated = time.time()

            self._save_user_reputation(reputation)

    # ========== MÉTODOS INTERNOS ==========

    def _save_post(self, post: Post):
        """Salva post no banco"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO feed_posts
            (id, author_id, author_username, content, timestamp, post_type,
             parent_post_id, thread_level, upvotes, downvotes, comments_count,
             retweets_count, shares_count, weight_score, is_pinned, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post.id, post.author_id, post.author_username, post.content,
            post.timestamp, post.post_type, post.parent_post_id,
            post.thread_level, post.upvotes, post.downvotes,
            post.comments_count, post.retweets_count, post.shares_count, post.weight_score,
            int(post.is_pinned), json.dumps(post.tags), json.dumps(post.metadata)
        ))

        conn.commit()
        conn.close()

    def _save_vote(self, vote: Vote):
        """Salva voto no banco"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._save_vote_with_conn(conn, vote)
            conn.commit()
        finally:
            conn.close()

    def _save_vote_with_conn(self, conn, vote: Vote):
        """Salva voto no banco usando conexão existente"""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO feed_votes
            (id, post_id, voter_id, voter_username, vote_type, vote_weight, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (vote.id, vote.post_id, vote.voter_id, vote.voter_username,
              vote.vote_type, vote.vote_weight, vote.timestamp))

    def _save_badge(self, badge: CommunityBadge):
        """Salva selo no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO community_badges
            (id, post_id, badge_type, awarded_by, awarded_by_username, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (badge.id, badge.post_id, badge.badge_type,
              badge.awarded_by, badge.awarded_by_username, badge.timestamp))

        conn.commit()
        conn.close()

    def _save_sub_thread(self, thread: SubThread):
        """Salva sub-thread no banco"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sub_threads
            (id, root_post_id, parent_thread_id, title, description,
             created_by, created_by_username, timestamp, posts_count,
             participants_count, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            thread.id, thread.root_post_id, thread.parent_thread_id,
            thread.title, thread.description, thread.created_by,
            thread.created_by_username, thread.timestamp,
            thread.posts_count, thread.participants_count, int(thread.is_active)
        ))

        conn.commit()
        conn.close()

    def _save_user_reputation(self, reputation: UserReputation):
        """Salva reputação do usuário"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO user_reputation
            (user_id, username, total_posts, total_votes_received,
             total_votes_given, positive_votes_received, badges_received,
             engagement_score, vote_weight, reputation_level, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reputation.user_id, reputation.username, reputation.total_posts,
            reputation.total_votes_received, reputation.total_votes_given,
            reputation.positive_votes_received, reputation.badges_received,
            reputation.engagement_score, reputation.vote_weight,
            reputation.reputation_level, reputation.last_updated
        ))

        conn.commit()
        conn.close()

    def _row_to_post_dict(self, row) -> Dict:
        """Converte row do banco para dict do post"""
        return {
            'id': row[0],
            'author_id': row[1],
            'author_username': row[2],
            'content': row[3],
            'timestamp': row[4],
            'post_type': row[5],
            'parent_post_id': row[6],
            'thread_level': row[7],
            'upvotes': row[8],
            'downvotes': row[9],
            'comments_count': row[10],
            'retweets_count': row[11],
            'shares_count': row[12],
            'weight_score': row[13],
            'is_pinned': bool(row[14]),
            'tags': json.loads(row[15]) if row[15] else [],
            'metadata': json.loads(row[16]) if row[16] else {},
            'net_votes': row[8] - row[9],
            'reputation_level': row[17] if len(row) > 17 else 'novato',
            'author_vote_weight': row[18] if len(row) > 18 else 1.0
        }

    def _get_post_badges(self, post_id: str) -> Dict[str, int]:
        """Obtém contagem de selos do post"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT badge_type, COUNT(*) as count
            FROM community_badges
            WHERE post_id = ?
            GROUP BY badge_type
        ''', (post_id,))

        badges = {}
        for row in cursor.fetchall():
            badges[row[0]] = row[1]

        conn.close()
        return badges

    def _get_post_comments(self, post_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Obtém comentários de um post"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        cursor.execute(f'''
            SELECT fp.*, ur.reputation_level, ur.vote_weight
            FROM feed_posts fp
            LEFT JOIN user_reputation ur ON fp.author_id = ur.user_id
            WHERE fp.parent_post_id = ?
            ORDER BY fp.weight_score DESC, fp.timestamp ASC
            LIMIT ? OFFSET ?
        ''', (post_id, limit, offset))

        comments = []
        for row in cursor.fetchall():
            comment_data = self._row_to_post_dict(row)
            comment_data['badges'] = self._get_post_badges(comment_data['id'])
            comments.append(comment_data)

        conn.close()
        return comments

    def _get_user_vote(self, post_id: str, user_id: str) -> Optional[Dict]:
        """Busca voto do usuário no post"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            return self._get_user_vote_with_conn(conn, post_id, user_id)
        finally:
            conn.close()

    def _get_user_vote_with_conn(self, conn, post_id: str, user_id: str) -> Optional[Dict]:
        """Busca voto do usuário no post usando conexão existente"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, vote_type, vote_weight, timestamp
            FROM feed_votes
            WHERE post_id = ? AND voter_id = ?
        ''', (post_id, user_id))

        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'vote_type': row[1],
                'vote_weight': row[2],
                'timestamp': row[3]
            }
        return None

    def _get_user_vote_weight(self, user_id: str) -> float:
        """Obtém peso do voto do usuário"""
        reputation = self.get_user_reputation(user_id)
        return reputation.vote_weight if reputation else 1.0

    def _calculate_thread_level(self, parent_post_id: str) -> int:
        """Calcula nível da thread"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT thread_level FROM feed_posts WHERE id = ?', (parent_post_id,))
        row = cursor.fetchone()
        conn.close()

        return (row[0] + 1) if row else 1

    def _recalculate_post_scores(self, post_id: str):
        """Recalcula pontuações do post com base nos votos ponderados"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._recalculate_post_scores_with_conn(conn, post_id)
            conn.commit()
        finally:
            conn.close()

    def _recalculate_post_scores_with_conn(self, conn, post_id: str):
        """Recalcula pontuações do post usando conexão existente"""
        cursor = conn.cursor()

        # Calcular votos ponderados
        cursor.execute('''
            SELECT
                SUM(CASE WHEN vote_type = 'up' THEN vote_weight ELSE 0 END) as weighted_up,
                SUM(CASE WHEN vote_type = 'down' THEN vote_weight ELSE 0 END) as weighted_down,
                COUNT(CASE WHEN vote_type = 'up' THEN 1 END) as up_count,
                COUNT(CASE WHEN vote_type = 'down' THEN 1 END) as down_count
            FROM feed_votes WHERE post_id = ?
        ''', (post_id,))

        result = cursor.fetchone()
        weighted_up = result[0] or 0
        weighted_down = result[1] or 0
        up_count = result[2] or 0
        down_count = result[3] or 0

        # Calcular score ponderado
        weight_score = weighted_up - weighted_down

        # Atualizar post
        cursor.execute('''
            UPDATE feed_posts
            SET upvotes = ?, downvotes = ?, weight_score = ?
            WHERE id = ?
        ''', (up_count, down_count, weight_score, post_id))

    def _increment_comments_count(self, post_id: str):
        """Incrementa contador de comentários"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE feed_posts
            SET comments_count = comments_count + 1
            WHERE id = ?
        ''', (post_id,))

        conn.commit()
        conn.close()

    def _update_user_stats(self, user_id: str, posts_increment: int = 0,
                          votes_given_increment: int = 0, badges_increment: int = 0):
        """Atualiza estatísticas do usuário"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._update_user_stats_with_conn(conn, user_id, posts_increment, votes_given_increment, badges_increment)
            conn.commit()
        finally:
            conn.close()

        # Recalcular reputação
        if posts_increment > 0 or votes_given_increment > 0 or badges_increment > 0:
            self.calculate_user_reputation(user_id)

    def _update_user_stats_with_conn(self, conn, user_id: str, posts_increment: int = 0,
                          votes_given_increment: int = 0, badges_increment: int = 0):
        """Atualiza estatísticas do usuário usando conexão existente"""
        cursor = conn.cursor()

        # Verificar se existe reputação
        cursor.execute('SELECT user_id FROM user_reputation WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()

        if not exists:
            # Criar reputação inicial
            user = self.db.get_user(user_id)
            if user:
                cursor.execute('''
                    INSERT INTO user_reputation
                    (user_id, username, last_updated)
                    VALUES (?, ?, ?)
                ''', (user_id, user['username'], time.time()))

        # Atualizar estatísticas
        cursor.execute('''
            UPDATE user_reputation
            SET total_posts = total_posts + ?,
                total_votes_given = total_votes_given + ?,
                badges_received = badges_received + ?,
                last_updated = ?
            WHERE user_id = ?
        ''', (posts_increment, votes_given_increment, badges_increment, time.time(), user_id))

    def _calculate_user_engagement_stats(self, user_id: str) -> Dict:
        """Calcula estatísticas de engajamento do usuário"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Estatísticas básicas
        cursor.execute('''
            SELECT
                COUNT(*) as total_posts,
                AVG(weight_score) as avg_score,
                SUM(upvotes + downvotes + comments_count) as total_engagement
            FROM feed_posts WHERE author_id = ?
        ''', (user_id,))

        stats = cursor.fetchone()
        total_posts = stats[0] or 0
        avg_score = stats[1] or 0
        total_engagement = stats[2] or 0

        # Calcular score de engajamento
        engagement_score = 1.0
        if total_posts > 0:
            engagement_score = min(5.0, 1 + (total_engagement / total_posts) * 0.1 + avg_score * 0.1)

        conn.close()

        return {
            'total_posts': total_posts,
            'avg_score': avg_score,
            'total_engagement': total_engagement,
            'engagement_score': engagement_score
        }

    def _user_has_given_badge(self, post_id: str, badge_type: str, user_id: str) -> bool:
        """Verifica se usuário já deu este selo para o post"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM community_badges
            WHERE post_id = ? AND badge_type = ? AND awarded_by = ?
        ''', (post_id, badge_type, user_id))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def _remove_vote(self, vote_id: str):
        """Remove voto"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._remove_vote_with_conn(conn, vote_id)
            conn.commit()
        finally:
            conn.close()

    def _remove_vote_with_conn(self, conn, vote_id: str):
        """Remove voto usando conexão existente"""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM feed_votes WHERE id = ?', (vote_id,))

    def _update_vote(self, vote_id: str, new_vote_type: str):
        """Atualiza tipo de voto"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._update_vote_with_conn(conn, vote_id, new_vote_type)
            conn.commit()
        finally:
            conn.close()

    def _update_vote_with_conn(self, conn, vote_id: str, new_vote_type: str):
        """Atualiza tipo de voto usando conexão existente"""
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE feed_votes SET vote_type = ?, timestamp = ?
            WHERE id = ?
        ''', (new_vote_type, time.time(), vote_id))

    # ========== PESQUISA ==========

    def search_posts(self, query: str, limit: int = 20) -> List[Dict]:
        """Pesquisa posts por conteúdo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM feed_posts
            WHERE content LIKE ? AND parent_post_id IS NULL
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{query}%', limit))

        posts = []
        for row in cursor.fetchall():
            post_dict = self._row_to_post_dict(row)
            posts.append(post_dict)

        conn.close()
        return posts

    def get_user_posts(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Obtém posts de um usuário específico"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM feed_posts
            WHERE author_id = ? AND parent_post_id IS NULL
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))

        posts = []
        for row in cursor.fetchall():
            post_dict = self._row_to_post_dict(row)
            posts.append(post_dict)

        conn.close()
        return posts


    # ========== RETWEETS ==========

    def create_retweet(self, original_post_id: str, user_id: str, username: str,
                      retweet_type: str = 'simple', comment: Optional[str] = None) -> Dict:
        """Cria um retweet (simples ou com comentário)"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()

        try:
            # Verificar se já retweetou
            cursor.execute('''
                SELECT id FROM feed_retweets WHERE original_post_id = ? AND user_id = ?
            ''', (original_post_id, user_id))

            if cursor.fetchone():
                raise Exception("Você já republicou este post")

            # Criar retweet
            retweet_id = f"rt_{time.time()}_{user_id[:8]}"
            cursor.execute('''
                INSERT INTO feed_retweets
                (id, original_post_id, user_id, username, retweet_type, comment, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (retweet_id, original_post_id, user_id, username, retweet_type, comment, time.time()))

            # Atualizar contador de retweets
            self._update_post_retweets_count_with_conn(conn, original_post_id)

            # Obter novo contador
            cursor.execute('SELECT retweets_count FROM feed_posts WHERE id = ?', (original_post_id,))
            retweets_count = cursor.fetchone()[0]

            conn.commit()
            return {
                "retweet_id": retweet_id,
                "retweets_count": retweets_count
            }
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _update_post_retweets_count(self, post_id: str):
        """Atualiza contador de retweets do post"""
        conn = sqlite3.connect(self.db.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            self._update_post_retweets_count_with_conn(conn, post_id)
            conn.commit()
        finally:
            conn.close()

    def _update_post_retweets_count_with_conn(self, conn, post_id: str):
        """Atualiza contador de retweets do post usando conexão existente"""
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM feed_retweets WHERE original_post_id = ?', (post_id,))
        retweets_count = cursor.fetchone()[0]
        cursor.execute('UPDATE feed_posts SET retweets_count = ? WHERE id = ?', (retweets_count, post_id))