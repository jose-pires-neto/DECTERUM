#!/usr/bin/env python3
"""
DECTERUM - Script de Instalação Automática com DHT
Configura tudo automaticamente para uso imediato com rede global
"""

import os
import sys
import subprocess
import shutil
import webbrowser
import time

def print_banner():
    banner = """
    ██████╗ ███████╗ ██████╗████████╗███████╗██████╗ ██╗   ██╗███╗   ███╗
    ██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗██║   ██║████╗ ████║
    ██║  ██║█████╗  ██║        ██║   █████╗  ██████╔╝██║   ██║██╔████╔██║
    ██║  ██║██╔══╝  ██║        ██║   ██╔══╝  ██╔══██╗██║   ██║██║╚██╔╝██║
    ██████╔╝███████╗╚██████╗   ██║   ███████╗██║  ██║╚██████╔╝██║ ╚═╝ ██║
    ╚═════╝ ╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝
    
    🌐 Rede Social Descentralizada com DHT Global - Instalação Automática
    """
    print(banner)

def check_python():
    """Verifica versão do Python"""
    print("🐍 Verificando Python...")
    
    if sys.version_info >= (3, 8):
        print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
        return True
    else:
        print(f"   ❌ Python {sys.version_info.major}.{sys.version_info.minor} - Requer 3.8+")
        print("   💡 Instale Python 3.8+ em: https://python.org")
        return False

def install_dependencies():
    """Instala dependências incluindo DHT"""
    print("📦 Instalando dependências (incluindo DHT)...")
    
    try:
        # Atualizar pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        print("   ✅ pip atualizado")
        
        # Instalar dependências do requirements.txt
        if os.path.exists("requirements.txt"):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          check=True, capture_output=True)
            print("   ✅ Dependências do requirements.txt instaladas")
        else:
            # Fallback para instalação manual das dependências essenciais
            dependencies = [
                "fastapi==0.104.1",
                "uvicorn[standard]==0.24.0", 
                "requests==2.31.0",
                "cryptography==41.0.7",
                "python-multipart==0.0.6",
                "aiohttp==3.9.1"
            ]
            
            for dep in dependencies:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                              check=True, capture_output=True)
                print(f"   ✅ {dep.split('==')[0]} instalado")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro na instalação: {e}")
        print("   💡 Tente instalar manualmente:")
        print("   pip install fastapi uvicorn requests cryptography aiohttp")
        return False

def create_directories():
    """Cria diretórios necessários"""
    print("📁 Criando estrutura de arquivos...")
    
    directories = ["static", "data", "logs"]
    
    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"   ✅ Criado: {dir_name}/")
        else:
            print(f"   ✅ Existe: {dir_name}/")

def check_files():
    """Verifica se os arquivos necessários existem"""
    print("🔍 Verificando arquivos...")
    
    required_files = {
        "app.py": "Backend principal com DHT",
        "dht_manager.py": "Sistema DHT Kademlia", 
        "requirements.txt": "Lista de dependências",
        "static/index.html": "Interface web",
        "static/styles.css": "Estilos da interface",
        "static/script.js": "Lógica JavaScript"
    }
    
    missing = []
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - {description}")
            missing.append(file_path)
    
    if missing:
        print("\n⚠️ Arquivos em falta detectados!")
        print("💡 Para uma instalação completa, certifique-se de ter todos os arquivos.")
        
        response = input("🤔 Continuar mesmo assim? (s/N): ").lower()
        if response != 's':
            return False
    
    return True

def create_start_scripts():
    """Cria scripts de inicialização"""
    print("🚀 Criando scripts de inicialização...")
    
    # Script Windows
    windows_script = '''@echo off
title DECTERUM - Rede Descentralizada Global
echo 🌐 Iniciando DECTERUM com DHT...
echo ⏳ Aguarde a inicialização da rede P2P...
set DECTERUM_DHT_ENABLED=true
python app.py
pause
'''
    
    # Script Unix/Linux/Mac
    unix_script = '''#!/bin/bash
echo "🌐 Iniciando DECTERUM com DHT..."
echo "⏳ Aguarde a inicialização da rede P2P..."
export DECTERUM_DHT_ENABLED=true
python3 app.py
'''
    
    # Script para DHT desabilitado (compatibilidade)
    windows_script_no_dht = '''@echo off
title DECTERUM - Modo Local
echo 🏠 Iniciando DECTERUM em modo local...
set DECTERUM_DHT_ENABLED=false
python app.py
pause
'''
    
    unix_script_no_dht = '''#!/bin/bash
echo "🏠 Iniciando DECTERUM em modo local..."
export DECTERUM_DHT_ENABLED=false
python3 app.py
'''
    
    try:
        # Scripts principais
        with open("start.bat", "w", encoding="utf-8") as f:
            f.write(windows_script)
        print("   ✅ start.bat criado (DHT habilitado)")
        
        with open("start.sh", "w", encoding="utf-8") as f:
            f.write(unix_script)
        os.chmod("start.sh", 0o755)
        print("   ✅ start.sh criado (DHT habilitado)")
        
        # Scripts de compatibilidade
        with open("start_local.bat", "w", encoding="utf-8") as f:
            f.write(windows_script_no_dht)
        print("   ✅ start_local.bat criado (apenas local)")
        
        with open("start_local.sh", "w", encoding="utf-8") as f:
            f.write(unix_script_no_dht)
        os.chmod("start_local.sh", 0o755)
        print("   ✅ start_local.sh criado (apenas local)")
        
    except Exception as e:
        print(f"   ⚠️ Erro criando scripts: {e}")

def test_installation():
    """Testa a instalação"""
    print("🧪 Testando instalação...")
    
    try:
        # Testar importações básicas
        import fastapi
        import uvicorn
        import requests
        import cryptography
        print("   ✅ Dependências básicas OK")
        
        # Testar importações do DHT
        try:
            import aiohttp
            import asyncio
            print("   ✅ Dependências DHT OK")
        except ImportError:
            print("   ⚠️ Dependências DHT não encontradas - DHT será desabilitado")
        
        # Verificar arquivos principais
        if os.path.exists("app.py"):
            print("   ✅ Backend principal OK")
        else:
            print("   ❌ app.py não encontrado")
            return False
        
        # Verificar DHT
        if os.path.exists("dht_manager.py"):
            print("   ✅ Sistema DHT OK")
        else:
            print("   ⚠️ dht_manager.py não encontrado - DHT será desabilitado")
        
        # Verificar interface
        if os.path.exists("static/index.html"):
            print("   ✅ Interface web OK")
        else:
            print("   ❌ Interface web não encontrada")
            return False
            
        return True
            
    except ImportError as e:
        print(f"   ❌ Erro de importação: {e}")
        return False

def test_dht_functionality():
    """Testa funcionalidade DHT"""
    print("🌐 Testando funcionalidade DHT...")
    
    try:
        # Verifica se pode importar o DHT manager
        if os.path.exists("dht_manager.py"):
            # Teste simples de importação
            sys.path.insert(0, os.getcwd())
            
            # Teste básico sem executar
            with open("dht_manager.py", "r") as f:
                content = f.read()
                if "class DecterumDHT" in content and "class KademliaDHT" in content:
                    print("   ✅ Estrutura DHT válida")
                    return True
                else:
                    print("   ⚠️ Estrutura DHT incompleta")
                    return False
        else:
            print("   ⚠️ DHT não instalado - funcionará apenas localmente")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Erro testando DHT: {e}")
        return False

def start_application():
    """Inicia a aplicação"""
    print("🎉 Instalação concluída com sucesso!")
    print("=" * 60)
    
    # Detecta capacidades
    has_dht = os.path.exists("dht_manager.py")
    
    if has_dht:
        print("🌍 DECTERUM DHT - Rede Global Detectada!")
        print("   • Descoberta automática de usuários no mundo")
        print("   • Comunicação P2P sem limites geográficos")
        print("   • Resistente à censura e descentralizado")
    else:
        print("🏠 DECTERUM Local - Rede Local Detectada")
        print("   • Funcionamento apenas na rede local")
        print("   • Para rede global, instale dht_manager.py")
    
    print("\n" + "=" * 60)
    
    response = input("🚀 Deseja iniciar o DECTERUM agora? (s/N): ").lower()
    
    if response == 's':
        print("\n🌐 Iniciando DECTERUM...")
        print("⏳ Aguarde alguns segundos...")
        
        # Escolhe qual versão iniciar
        if has_dht:
            print("🌍 Modo: Rede Global DHT")
            env_vars = {"DECTERUM_DHT_ENABLED": "true"}
        else:
            print("🏠 Modo: Rede Local")
            env_vars = {"DECTERUM_DHT_ENABLED": "false"}
        
        try:
            # Iniciar em processo separado
            if os.name == 'nt':  # Windows
                subprocess.Popen([sys.executable, "app.py"], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE,
                               env={**os.environ, **env_vars})
            else:  # Unix/Linux/Mac
                subprocess.Popen([sys.executable, "app.py"],
                               env={**os.environ, **env_vars})
            
            # Aguardar inicialização
            time.sleep(5 if has_dht else 3)
            
            # Abrir no navegador
            webbrowser.open("http://localhost:8000")
            
            print("✅ DECTERUM iniciado!")
            print("📱 Interface aberta no navegador")
            print("🌐 Acesse: http://localhost:8000")
            
            if has_dht:
                print("⏳ DHT inicializando... Aguarde 1-2 minutos para descoberta global")
            
        except Exception as e:
            print(f"❌ Erro ao iniciar: {e}")
            print("💡 Execute manualmente:")
            if has_dht:
                print("   python app.py  (com DHT)")
                print("   ou start.bat / ./start.sh")
            else:
                print("   python app.py  (apenas local)")
    
    else:
        print("\n📋 Para iniciar depois:")
        if has_dht:
            print("   🌍 Rede Global:")
            print("     • Windows: execute start.bat")
            print("     • Linux/Mac: execute ./start.sh")
            print("   🏠 Apenas Local:")
            print("     • Windows: execute start_local.bat")
            print("     • Linux/Mac: execute ./start_local.sh")
        else:
            print("   • Windows: execute start.bat")
            print("   • Linux/Mac: execute ./start.sh")
            print("   • Ou: python app.py")
        
        print("\n🌐 Acesse: http://localhost:8000")

def show_next_steps():
    """Mostra próximos passos"""
    print("\n" + "="*60)
    print("🎯 PRÓXIMOS PASSOS")
    print("="*60)
    
    has_dht = os.path.exists("dht_manager.py")
    
    if has_dht:
        print("🌍 MODO REDE GLOBAL (DHT):")
        print("1. 🆔 Anote seu ID de usuário (gerado automaticamente)")
        print("2. 🌐 Aguarde 1-2 minutos para conectar à rede global")
        print("3. 🔍 Use 'Discover Network Nodes' para encontrar usuários") 
        print("4. ➕ Adicione contatos usando IDs de qualquer lugar do mundo")
        print("5. 💬 Comece a conversar globalmente!")
        print("\n🚀 FUNCIONALIDADES GLOBAIS:")
        print("   • Busca automática de usuários no mundo")
        print("   • Mensagens chegam em qualquer país")
        print("   • Rede cresce automaticamente")
        print("   • Resistente à censura")
    else:
        print("🏠 MODO REDE LOCAL:")
        print("1. 🆔 Anote seu ID de usuário (gerado automaticamente)")
        print("2. 👥 Compartilhe seu ID com amigos na mesma WiFi")
        print("3. ➕ Adicione contatos usando os IDs deles")
        print("4. 💬 Comece a conversar!")
        print("\n🌍 PARA REDE GLOBAL:")
        print("   • Instale dht_manager.py do repositório")
        print("   • Reinicie com DHT habilitado")
    
    print("\n🌍 ACESSO EXTERNO:")
    print("   • Configure Cloudflare Tunnel para acesso pelo celular")
    print("   • Veja o README.md para instruções detalhadas")
    print("\n🔧 SUPORTE:")
    print("   • GitHub Issues para bugs")
    print("   • README.md para documentação completa")
    print("="*60)

def main():
    """Função principal"""
    print_banner()
    
    # Verificações
    if not check_python():
        sys.exit(1)
    
    if not check_files():
        print("\n❌ Arquivos necessários não encontrados!")
        print("💡 Para instalação completa, certifique-se de ter:")
        print("   • app.py (obrigatório)")
        print("   • dht_manager.py (para rede global)")
        print("   • static/index.html (obrigatório)")
        print("   • static/styles.css e script.js (recomendado)")
        sys.exit(1)
    
    # Instalação
    create_directories()
    
    if not install_dependencies():
        print("\n❌ Falha na instalação das dependências!")
        print("💡 Tente instalar manualmente:")
        print("   pip install fastapi uvicorn requests cryptography aiohttp")
        sys.exit(1)
    
    create_start_scripts()
    
    # Testes
    if not test_installation():
        print("\n❌ Teste de instalação falhou!")
        sys.exit(1)
    
    # Teste DHT (opcional)
    test_dht_functionality()
    
    # Finalização
    start_application()
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Instalação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)