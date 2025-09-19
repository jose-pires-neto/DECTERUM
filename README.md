# 🌐 DECTERUM - Rede Social Descentralizada

Sistema P2P completo com interface tipo app móvel para chat, feed social e compartilhamento de mídia - tudo descentralizado!

## ⚡ Instalação Ultra-Rápida

### 1. Clone e Instale
```bash
git clone <repository>
cd decterum
pip install -r requirements.txt
```

### 2. Execute
```bash
python app.py
```

### 3. Acesse
**Local:** http://localhost:8000  
**Mobile:** Configure o túnel Cloudflare (veja abaixo)

## 🎨 Nova Interface App-Style

A interface foi completamente redesenhada para parecer um app móvel moderno:

### 📱 Menu Inferior Flutuante
- **💬 Chat**: Conversas e mensagens
- **🐦 Feed**: Rede social (em desenvolvimento)  
- **🎥 Vídeos**: Compartilhamento de mídia (em desenvolvimento)
- **⚙️ Config**: Configurações e informações da rede

### 🔥 Funcionalidades do Chat
- **Lista de contatos** estilo WhatsApp
- **Mensagens em tempo real** com interface moderna
- **Adicionar contatos** por ID de usuário
- **Design responsivo** otimizado para mobile e desktop

## 🌍 Acesso Externo (Cloudflare Tunnel)

### Método 1: Script Automático (Recomendado)
```bash
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
- ✅ **100% Responsivo**: Funciona perfeitamente em todos os dispositivos
- ✅ **Menu Inferior Flutuante**: Navegação intuitiva entre seções
- ✅ **Cloudflare Tunnel**: Acesso externo automático
- ✅ **Persistência**: Mensagens salvas até entrega
- ✅ **Descoberta Automática**: Encontra outros nós na rede

## 🚀 Recursos em Desenvolvimento

### 🐦 Feed Social (Próxima Atualização)
- Posts e timeline descentralizados
- Curtidas e comentários P2P
- Hashtags e descoberta de conteúdo
- Sistema de seguir/seguidor

### 🎥 Vídeos Descentralizados  
- Upload e compartilhamento P2P
- Streaming descentralizado
- Sistema de likes/dislikes
- Comentários por vídeo

### 🔐 Melhorias de Segurança
- Chaves de criptografia por usuário
- Verificação de identidade
- Moderação descentralizada

## 🛠️ Estrutura Simplificada

```
DECTERUM/
├── app.py                    # Backend completo otimizado
├── static/
│   └── index.html           # Interface app-style responsiva  
├── setup_cloudflare.py     # Configuração automática do túnel
├── install.py               # Instalação automática
├── requirements.txt         # Dependências mínimas
├── .gitignore              # Arquivos a ignorar
├── README.md               # Este guia
└── decterum.db             # Database local (auto-criado)
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
- 🔄 Feed social básico

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
git clone <repository>
cd decterum
python install.py
```
E pronto! Sua rede descentralizada está funcionando! 🎉