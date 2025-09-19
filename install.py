#!/usr/bin/env python3
"""
DECTERUM - Script de Instalação Automática
Configura tudo automaticamente para uso imediato
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
    
    🌐 Rede Social Descentralizada - Instalação Automática
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
    """Instala dependências"""
    print("📦 Instalando dependências...")
    
    try:
        # Atualizar pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        print("   ✅ pip atualizado")
        
        # Instalar dependências
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("   ✅ Dependências instaladas")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro na instalação: {e}")
        print("   💡 Tente: pip install fastapi uvicorn requests cryptography")
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
        "app.py": "Backend principal",
        "requirements.txt": "Lista de dependências",
        "static/index.html": "Interface web"
    }
    
    missing = []
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - {description}")
            missing.append(file_path)
    
    return len(missing) == 0

def create_start_scripts():
    """Cria scripts de inicialização"""
    print("🚀 Criando scripts de inicialização...")
    
    # Script Windows
    windows_script = '''@echo off
title DECTERUM - Rede Descentralizada
echo 🌐 Iniciando DECTERUM...
python app.py
pause
'''
    
    # Script Unix/Linux/Mac
    unix_script = '''#!/bin/bash
echo "🌐 Iniciando DECTERUM..."
python3 app.py
'''
    
    try:
        # Windows
        with open("start.bat", "w", encoding="utf-8") as f:
            f.write(windows_script)
        print("   ✅ start.bat criado")
        
        # Unix/Linux/Mac
        with open("start.sh", "w", encoding="utf-8") as f:
            f.write(unix_script)
        os.chmod("start.sh", 0o755)
        print("   ✅ start.sh criado")
        
    except Exception as e:
        print(f"   ⚠️ Erro criando scripts: {e}")

def test_installation():
    """Testa a instalação"""
    print("🧪 Testando instalação...")
    
    try:
        # Testar importações
        import fastapi
        import uvicorn
        import requests
        import cryptography
        print("   ✅ Importações OK")
        
        # Verificar arquivos principais
        if os.path.exists("app.py") and os.path.exists("static/index.html"):
            print("   ✅ Arquivos principais OK")
            return True
        else:
            print("   ❌ Arquivos principais não encontrados")
            return False
            
    except ImportError as e:
        print(f"   ❌ Erro de importação: {e}")
        return False

def start_application():
    """Inicia a aplicação"""
    print("🎉 Instalação concluída com sucesso!")
    print("=" * 60)
    
    response = input("🚀 Deseja iniciar o DECTERUM agora? (s/N): ").lower()
    
    if response == 's':
        print("\n🌐 Iniciando DECTERUM...")
        print("⏳ Aguarde alguns segundos...")
        
        try:
            # Iniciar em processo separado
            if os.name == 'nt':  # Windows
                subprocess.Popen([sys.executable, "app.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Unix/Linux/Mac
                subprocess.Popen([sys.executable, "app.py"])
            
            # Aguardar inicialização
            time.sleep(3)
            
            # Abrir no navegador
            webbrowser.open("http://localhost:8000")
            
            print("✅ DECTERUM iniciado!")
            print("📱 Interface aberta no navegador")
            print("🌐 Acesse: http://localhost:8000")
            
        except Exception as e:
            print(f"❌ Erro ao iniciar: {e}")
            print("💡 Execute manualmente: python app.py")
    
    else:
        print("\n📋 Para iniciar depois:")
        print("   • Windows: execute start.bat")
        print("   • Linux/Mac: execute ./start.sh")
        print("   • Ou: python app.py")
        print("\n🌐 Acesse: http://localhost:8000")

def show_next_steps():
    """Mostra próximos passos"""
    print("\n" + "="*60)
    print("🎯 PRÓXIMOS PASSOS")
    print("="*60)
    print("1. 🆔 Anote seu ID de usuário (gerado automaticamente)")
    print("2. 👥 Compartilhe seu ID com amigos")
    print("3. ➕ Adicione contatos usando os IDs deles")
    print("4. 💬 Comece a conversar!")
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
        print("💡 Certifique-se de ter:")
        print("   • app.py")
        print("   • requirements.txt") 
        print("   • static/index.html")
        sys.exit(1)
    
    # Instalação
    create_directories()
    
    if not install_dependencies():
        print("\n❌ Falha na instalação das dependências!")
        print("💡 Tente instalar manualmente:")
        print("   pip install fastapi uvicorn requests cryptography")
        sys.exit(1)
    
    create_start_scripts()
    
    # Teste
    if not test_installation():
        print("\n❌ Teste de instalação falhou!")
        sys.exit(1)
    
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
