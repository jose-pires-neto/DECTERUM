# 🌐 DECTERUM - Rede Social Descentralizada

Sistema P2P completo com DHT global, descoberta automática de peers e interface tipo app móvel - totalmente descentralizado!

## ⚡ Instalação Automática (Recomendada)

### 1. Clone o Repositório
```bash
git clone https://github.com/jose-pires-neto/DECTERUM.git
cd DECTERUM
```

### 2. Instalação Automática
```bash
python install.py
```
O script detecta seu sistema e instala tudo automaticamente com dependências compatíveis.

### 3. Instalação Manual (se necessário)
```bash
pip install fastapi>=0.110.0 uvicorn[standard] requests>=2.32.0 cryptography>=43.0.0 python-multipart>=0.0.9 aiohttp>=3.10.0 psutil>=5.9.0
```

### 4. Execute
```bash
python app.py
```

### 5. Acesse
**Local:** http://localhost:8000
**Mobile:** Configure o túnel Cloudflare (veja abaixo)

## 🔧 Solução de Problemas

### Erro na Instalação
Se `python install.py` falhar:
1. **Python 3.13**: Use versões compatíveis (instalação automática resolve)
2. **Dependências**: Execute `pip install --upgrade pip` primeiro
3. **Compilação**: Windows pode precisar do Visual Studio Build Tools

### Cloudflare Tunnel Não Encontrado
```bash
# Instalação automática do cloudflared
python setup_cloudflare_auto.py
```

### Versões Testadas
- ✅ Python 3.8 - 3.13
- ✅ Windows 10/11
- ✅ Linux Ubuntu/Debian
- ✅ macOS (Intel e Apple Silicon)

## 🎨 Nova Interface App-Style

A interface foi completamente redesenhada para parecer um app móvel moderno:

### 📱 Menu Inferior Flutuante
- **💬 Chat**: Conversas e mensagens P2P
- **🐦 Feed**: Rede social descentralizada ✅ IMPLEMENTADO
- **🎥 Vídeos**: Compartilhamento de mídia ✅ IMPLEMENTADO
- **⚙️ Config**: Configurações e informações da rede

### 🔥 Funcionalidades do Chat
- **Lista de contatos** estilo WhatsApp
- **Mensagens em tempo real** com interface moderna
- **Adicionar contatos** por ID de usuário
- **Design responsivo** otimizado para mobile e desktop

### 🐦 Funcionalidades do Feed
- **Posts em tempo real** com sistema de timeline
- **Curtidas e comentários** descentralizados
- **Hashtags** para descoberta de conteúdo
- **Interface estilo Instagram/Twitter**
- **Criação de posts** com texto e emojis

### 🎥 Funcionalidades de Vídeos
- **Upload de vídeos** até 10GB
- **Shorts** (≤60s) e vídeos longos (até 10h)
- **Player integrado** com controles completos
- **Sistema de likes/dislikes** e comentários
- **Trending** e busca avançada
- **Playlists personalizadas**
- **Analytics** para criadores de conteúdo
- **Interface estilo YouTube** responsiva

## 🌍 Acesso Externo (Cloudflare Tunnel)

### Método 1: Script Automático (Recomendado)
```bash
# Instalar e configurar cloudflared automaticamente
python setup_cloudflare_auto.py

# Configurar túnel automaticamente
python setup_cloudflare.py

# Ou para porta específica
python setup_cloudflare.py 8001
```

### Método 2: Manual

#### 1. Instalar Cloudflared
```bash
# Windows
winget install Cloudflare.cloudflared

# macOS  
brew install cloudflare/cloudflare/cloudflared

# Linux (Ubuntu/Debian)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

#### 2. Iniciar Túnel Rápido
```bash
# Terminal 1: Iniciar DECTERUM
python app.py

# Terminal 2: Iniciar túnel
cloudflared tunnel --url http://localhost:8000
```

#### 3. Copiar URL
O Cloudflared mostrará uma URL tipo: `https://abc123.trycloudflare.com`

## 📱 Como Usar

### Primeiro Acesso
1. Abra http://localhost:8000
2. Seu ID será gerado automaticamente
3. Anote seu ID na seção **Configurações**
4. Compartilhe com amigos para adicionar contatos

### ➕ Adicionar Contatos
1. Vá para a seção **Chat**
2. Clique em **"+ Adicionar"**
3. Cole o ID do usuário do seu amigo
4. Digite um nome para identificá-lo
5. Toque em **"Adicionar"**

### 💬 Enviar Mensagens
1. Selecione um contato da lista
2. Digite sua mensagem
3. Pressione Enter ou toque no botão enviar
4. Use a seta **←** para voltar à lista de contatos

### ⚙️ Configurações
- **Perfil**: Veja e edite seu username
- **Rede**: Status de conexão e peers
- **Túnel**: URL externa para acesso móvel
- **Ações**: Buscar nós e editar perfil

## 🔗 Conectar Dispositivos

### Acesso Local (Mesma WiFi)
```bash
# Descobrir IP local
ipconfig  # Windows
ifconfig  # Linux/Mac

# Acessar de outro dispositivo
http://[SEU-IP]:8000
```

### Acesso Global (Cloudflare Tunnel)
1. Configure o túnel com `python setup_cloudflare.py`
2. Compartilhe a URL gerada (ex: `https://abc123.trycloudflare.com`)
3. Acesse de qualquer lugar pelo celular/computador

## 🌐 Rede Multi-Nós

Para testar localmente com múltiplos usuários:

```bash
# Terminal 1
python app.py --port 8000

# Terminal 2  
python app.py --port 8001

# Terminal 3
python app.py --port 8002
```

Acesse:
- http://localhost:8000 (Usuário 1)
- http://localhost:8001 (Usuário 2)  
- http://localhost:8002 (Usuário 3)

## ✨ Recursos Atuais

- ✅ **Interface App-Style**: Design moderno tipo aplicativo móvel
- ✅ **Chat P2P**: Mensagens criptografadas em tempo real
- ✅ **Sistema de Contatos**: Adicione usuários por ID único
- ✅ **Feed Social**: Posts, curtidas e comentários descentralizados
- ✅ **Vídeos P2P**: Upload, streaming e interação com vídeos
- ✅ **Sistema Modular**: Arquitetura escalável por módulos
- ✅ **100% Responsivo**: Funciona perfeitamente em todos os dispositivos
- ✅ **Menu Inferior Flutuante**: Navegação intuitiva entre seções
- ✅ **Cloudflare Tunnel**: Acesso externo automático
- ✅ **Persistência**: Dados salvos localmente no SQLite
- ✅ **Descoberta Automática**: Encontra outros nós na rede

## 🚀 Recursos em Desenvolvimento

### 🔗 Integração P2P Avançada
- Compartilhamento direto de arquivos grandes
- Streaming de vídeos otimizado
- Cache distribuído de conteúdo
- Sincronização offline

### 🎥 Vídeos Descentralizados ✅ IMPLEMENTADO
- ✅ Upload e compartilhamento P2P
- ✅ Interface estilo YouTube/TikTok
- ✅ Sistema de likes/dislikes
- ✅ Comentários por vídeo
- ✅ Shorts (vídeos curtos ≤60s)
- ✅ Trending e busca de vídeos
- ✅ Playlists e analytics

### 🔐 Melhorias de Segurança
- Chaves de criptografia por usuário
- Verificação de identidade
- Moderação descentralizada

## 🛠️ Estrutura do Projeto

```
DECTERUM/
├── app.py                           # Backend principal (legacy)
├── src/                            # Código modularizado
│   ├── api/
│   │   └── main.py                # API principal FastAPI
│   ├── core/
│   │   ├── database.py            # Sistema de banco de dados
│   │   └── node.py                # Nó P2P
│   ├── modules/                   # Módulos funcionais
│   │   ├── chat/                  # Sistema de chat
│   │   │   ├── models.py         # Modelos de dados
│   │   │   ├── routes.py         # Endpoints da API
│   │   │   └── service.py        # Lógica de negócio
│   │   ├── feed/                  # Rede social
│   │   │   ├── models.py         # Posts, likes, comentários
│   │   │   ├── routes.py         # API do feed
│   │   │   └── service.py        # Lógica do feed
│   │   └── video/                 # Sistema de vídeos
│   │       ├── models.py         # Vídeos, playlists, analytics
│   │       ├── routes.py         # API de vídeos
│   │       └── service.py        # Lógica de vídeos
│   └── network/                   # Infraestrutura de rede
│       ├── cloudflare.py         # Túneis Cloudflare
│       ├── dht.py                # DHT Kademlia
│       └── discovery.py          # Descoberta de peers
├── static/                        # Interface web
│   ├── index.html                # Interface principal
│   ├── styles.css                # Estilos globais
│   ├── script.js                 # JavaScript principal
│   ├── js/
│   │   ├── module-loader.js      # Sistema de carregamento modular
│   │   └── modules/              # Módulos frontend
│   │       ├── feed.js           # JavaScript do feed
│   │       ├── videos.js         # JavaScript dos vídeos
│   │       └── video-demo-data.js # Dados de demonstração
│   ├── css/modules/              # CSS modular
│   │   ├── feed.css             # Estilos do feed
│   │   └── videos.css           # Estilos dos vídeos
│   └── html/modules/             # HTML modular
│       ├── feed.html            # Interface do feed
│       └── videos.html          # Interface dos vídeos
├── install.py                    # Instalação automática
├── setup_cloudflare.py         # Configuração túnel
├── setup_cloudflare_auto.py    # Instalação cloudflared
├── requirements.txt             # Dependências
├── README.md                    # Esta documentação
├── data/                        # Dados de usuários (auto-criado)
├── logs/                        # Logs do sistema (auto-criado)
└── decterum.db                 # Database SQLite (auto-criado)
```

## 💡 Dicas de Uso

### 📱 Para Uso Móvel
- Configure túnel Cloudflare para acesso externo
- Interface otimizada para toque
- Menu inferior sempre acessível
- Mensagens com design tipo WhatsApp

### 🔧 Para Desenvolvimento  
- Use `python app.py --port XXXX` para múltiplos nós
- Logs detalhados no terminal
- API REST completa em `/api/*`
- Database SQLite para facilidade

### 🌍 Para Compartilhar
- Configure túnel: `python setup_cloudflare.py`
- Compartilhe URL gerada com amigos
- Eles acessam direto pelo navegador
- Não precisa instalar nada!

## 🔐 Segurança

- **Criptografia**: Todas as mensagens são criptografadas
- **P2P Puro**: Sem servidores centrais
- **IDs Únicos**: Cada usuário tem identificação única
- **Dados Locais**: Tudo armazenado no seu dispositivo
- **Túneis Seguros**: HTTPS automático via Cloudflare

## 🌟 Diferenciais

### vs WhatsApp/Telegram
- ✅ **Descentralizado** - Sem servidores da empresa
- ✅ **Open Source** - Código aberto e auditável  
- ✅ **Sem Número** - Use IDs em vez de telefone
- ✅ **Multiplataforma** - Funciona em qualquer navegador

### vs Discord/Slack  
- ✅ **P2P Real** - Conexão direta entre usuários
- ✅ **Sem Limites** - Não há restrições de servidor
- ✅ **Privacy Total** - Seus dados ficam com você

### vs Redes Sociais Tradicionais
- ✅ **Sem Algoritmos** - Você controla o que vê
- ✅ **Sem Censura** - Comunicação livre
- ✅ **Sem Tracking** - Zero coleta de dados

## 📞 Suporte

- **🐛 Bugs**: Abra uma issue no GitHub
- **💡 Sugestões**: Discussões no repositório  
- **📚 Docs**: Este README e comentários no código
- **🆘 Ajuda**: Use a seção de configurações no app

## 🎯 Roadmap 2025

### Q1 2025
- ✅ Chat P2P funcional
- ✅ Interface mobile-first
- ✅ Cloudflare Tunnel
- ✅ Feed social completo
- ✅ Sistema de vídeos P2P
- ✅ Arquitetura modular

### Q2 2025
- 🔄 Sistema de arquivos P2P
- 🔄 Streaming de vídeo
- 🔄 Apps descentralizados
- 🔄 Marketplace P2P

### Q3 2025
- 🔄 Protocolo blockchain próprio
- 🔄 Tokens de reputação
- 🔄 DHT global
- 🔄 Bridge com outras redes

---

**DECTERUM** - O futuro da internet é descentralizado 🚀

*Seus dados. Sua rede. Sua escolha.*

### 🔥 Comece Agora
```bash
git clone https://github.com/jose-pires-neto/DECTERUM.git
cd DECTERUM
python install.py
```
E pronto! Sua rede descentralizada está funcionando! 🎉

## 📋 Changelog

### v3.0 (Atual)
- ✅ **Sistema Modular**: Arquitetura completamente modularizada
- ✅ **Feed Social**: Posts, curtidas e comentários P2P
- ✅ **Vídeos P2P**: Sistema completo de vídeos estilo YouTube
- ✅ **Interface Modular**: Frontend carregado dinamicamente
- ✅ **API RESTful**: Endpoints organizados por módulos
- ✅ **Banco Modular**: Estrutura de dados escalável

### v2.3 (Anterior)
- ✅ **Compatibilidade Universal**: Python 3.8-3.13
- ✅ **Instalação Robusta**: Script install.py melhorado
- ✅ **FastAPI Moderno**: Migrado para lifespan (sem warnings)
- ✅ **Cloudflared Auto**: Instalação automática de túneis
- ✅ **Dependências Atualizadas**: Versões compatíveis com Python 3.13

### v2.2 (Anterior)
- ✅ Interface app-style mobile-first
- ✅ DHT global funcional
- ✅ Descoberta automática LAN/WAN
- ✅ Sistema P2P robusto
