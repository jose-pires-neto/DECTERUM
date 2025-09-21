# 🌟 DECTERUM Feed Social - API Documentation

Sistema de feed social descentralizado com funcionalidades avançadas implementado na aplicação DECTERUM.

## 🚀 Funcionalidades Implementadas

### ✅ Sistema de "Peso de Voto" Dinâmico
- Usuários engajados têm votos que valem mais
- Sistema de reputação baseado em:
  - Histórico de contribuições
  - Engajamento na comunidade
  - Precisão dos votos dados
  - Selos comunitários recebidos
- Evita manipulação de bots criando "autoridade orgânica"

### ✅ Subtemas Descentralizados (Sub-threads)
- Criação de ramificações dentro de posts
- Sistema de "nós de conversa" organizados
- Evita poluição do feed principal
- Threads aninhadas com profundidade ilimitada

### ✅ Selos Comunitários
- Posts podem receber selos votados pelos usuários
- Tipos disponíveis: Engraçado, Informativo, Polêmico, Útil, Criativo, etc.
- Cria identidade sem dependência de algoritmo
- Sistema de reputação baseado em selos recebidos

## 🔗 Endpoints da API

### Posts

#### `POST /api/feed/posts`
Cria um novo post
```json
{
  "content": "Conteúdo do post",
  "post_type": "text",
  "parent_post_id": null,
  "tags": ["tag1", "tag2"]
}
```

#### `GET /api/feed/posts`
Lista posts do feed
- `?limit=50` - Quantidade de posts
- `?offset=0` - Offset para paginação
- `?sort_by=timestamp` - Ordenação: timestamp, weight, engagement

#### `GET /api/feed/posts/{post_id}`
Obtém post específico com comentários e selos

#### `GET /api/feed/posts/{post_id}/comments`
Lista comentários de um post

### Votação

#### `POST /api/feed/posts/{post_id}/vote`
Vota em um post
```json
{
  "vote_type": "up" // ou "down"
}
```

### Selos Comunitários

#### `POST /api/feed/posts/{post_id}/badges`
Atribui selo a um post
```json
{
  "badge_type": "funny" // tipos: funny, informative, controversial, helpful, creative, etc.
}
```

#### `GET /api/feed/posts/{post_id}/badges`
Lista selos de um post

#### `GET /api/feed/badge-types`
Lista tipos de selos disponíveis

### Sub-threads

#### `POST /api/feed/posts/{post_id}/threads`
Cria sub-thread para um post
```json
{
  "title": "Título da discussão",
  "description": "Descrição opcional",
  "parent_thread_id": null
}
```

#### `GET /api/feed/posts/{post_id}/threads`
Lista sub-threads de um post

### Reputação

#### `GET /api/feed/users/{user_id}/reputation`
Obtém reputação de um usuário

#### `GET /api/feed/me/reputation`
Obtém sua própria reputação

## 📊 Sistema de Reputação

### Níveis de Reputação
- **Novato**: Usuário inicial (peso voto: 1.0x)
- **Ativo**: Usuário engajado (peso voto: até 2.0x)
- **Experiente**: Contribuidor regular (peso voto: até 3.0x)
- **Especialista**: Membro respeitado (peso voto: até 4.0x)
- **Lenda**: Elite da comunidade (peso voto: até 5.0x)

### Cálculo do Peso do Voto
```
peso_final = 1.0 + bonus_engajamento + bonus_precisao + bonus_selos
max_peso = 5.0x
```

- **Bônus Engajamento**: Baseado em posts e interações
- **Bônus Precisão**: Histórico de votos bem-sucedidos
- **Bônus Selos**: Selos comunitários recebidos

## 🎯 Tipos de Selos Disponíveis

- 😄 **Engraçado**: Para posts divertidos
- 📚 **Informativo**: Conteúdo educativo
- 🔥 **Polêmico**: Discussões acaloradas
- 🤝 **Útil**: Posts que ajudam outros
- 🎨 **Criativo**: Conteúdo original
- 💡 **Perspicaz**: Insights valiosos
- ✍️ **Bem Escrito**: Qualidade de texto
- ✅ **Preciso**: Informação confiável

## 🗄️ Estrutura do Banco de Dados

### Tabelas Criadas
- `feed_posts`: Posts e comentários
- `feed_votes`: Votos com peso
- `community_badges`: Selos comunitários
- `user_reputation`: Reputação dos usuários
- `sub_threads`: Sub-threads de discussão

### Índices para Performance
- Timestamp dos posts
- Autor dos posts
- Posts pai (para comentários)
- Votos por post
- Selos por post

## 🚦 Como Usar

1. **Iniciar aplicação**: `python app.py`
2. **Acessar**: `http://localhost:8000`
3. **API Base**: `http://localhost:8000/api/feed/`
4. **Documentação**: `http://localhost:8000/docs`

## 🔧 Funcionalidades Técnicas

### Prevenção Anti-Spam
- Limite de votos por tempo
- Validação de duplicatas
- Sistema de reputação como filtro

### Performance
- Índices otimizados
- Consultas eficientes
- Cache de reputação

### Segurança
- Autenticação obrigatória
- Validação de entrada
- Sanitização de dados

## 🎮 Exemplos de Uso

### Criar Post
```bash
curl -X POST http://localhost:8000/api/feed/posts \
  -H "Content-Type: application/json" \
  -d '{"content": "Meu primeiro post no feed!"}'
```

### Votar em Post
```bash
curl -X POST http://localhost:8000/api/feed/posts/POST_ID/vote \
  -H "Content-Type: application/json" \
  -d '{"vote_type": "up"}'
```

### Atribuir Selo
```bash
curl -X POST http://localhost:8000/api/feed/posts/POST_ID/badges \
  -H "Content-Type: application/json" \
  -d '{"badge_type": "informative"}'
```

### Criar Sub-thread
```bash
curl -X POST http://localhost:8000/api/feed/posts/POST_ID/threads \
  -H "Content-Type: application/json" \
  -d '{"title": "Discussão específica", "description": "Vamos debater este ponto"}'
```

## 🌍 Integração P2P

O sistema foi projetado para funcionar em rede descentralizada:
- Posts sincronizados entre peers
- Reputação distribuída
- Selos validados pela rede
- Sub-threads compartilhadas

## 📈 Próximos Passos

- [ ] Interface web para o feed
- [ ] Sincronização P2P de posts
- [ ] Algoritmo de ranking avançado
- [ ] Sistema de moderação comunitária
- [ ] Estatísticas detalhadas
- [ ] Exportação de dados

---

**🎉 Sistema implementado com sucesso!**

Todas as funcionalidades solicitadas estão funcionais e integradas na aplicação DECTERUM.