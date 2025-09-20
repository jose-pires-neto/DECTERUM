#!/usr/bin/env python3
"""
Setup automático do Cloudflare Tunnel para DECTERUM
Detecta e instala cloudflared automaticamente
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import shutil

def detect_system():
    """Detecta o sistema operacional"""
    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "windows":
        if "64" in arch or "amd64" in arch:
            return "windows-amd64"
        else:
            return "windows-386"
    elif system == "darwin":  # macOS
        if "arm" in arch or "m1" in arch or "m2" in arch:
            return "darwin-arm64"
        else:
            return "darwin-amd64"
    elif system == "linux":
        if "64" in arch or "amd64" in arch:
            return "linux-amd64"
        elif "arm" in arch:
            return "linux-arm64"
        else:
            return "linux-386"
    else:
        return None

def check_cloudflared():
    """Verifica se cloudflared já está instalado"""
    try:
        result = subprocess.run(['cloudflared', '--version'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Cloudflared já instalado: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    # Verificar caminhos locais
    local_paths = ['./cloudflared', './cloudflared.exe']
    for path in local_paths:
        if os.path.exists(path):
            print(f"✅ Cloudflared encontrado em: {path}")
            return True

    return False

def install_cloudflared_windows():
    """Instala cloudflared no Windows"""
    print("📦 Instalando cloudflared no Windows...")

    # Tentar winget primeiro
    try:
        subprocess.run(['winget', 'install', '--id', 'Cloudflare.cloudflared',
                       '--accept-package-agreements', '--accept-source-agreements'],
                      check=True, capture_output=True)
        print("✅ Cloudflared instalado via winget")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Winget falhou, tentando download direto...")

    # Download direto
    try:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        print("📥 Baixando cloudflared...")
        urllib.request.urlretrieve(url, "cloudflared.exe")
        print("✅ Cloudflared baixado como cloudflared.exe")

        # Testar se funciona
        result = subprocess.run(['./cloudflared.exe', '--version'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Cloudflared funcionando: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"❌ Erro no download: {e}")

    return False

def install_cloudflared_macos():
    """Instala cloudflared no macOS"""
    print("📦 Instalando cloudflared no macOS...")

    # Tentar homebrew primeiro
    try:
        subprocess.run(['brew', 'install', 'cloudflare/cloudflare/cloudflared'],
                      check=True, capture_output=True)
        print("✅ Cloudflared instalado via homebrew")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Homebrew falhou, tentando download direto...")

    # Download direto
    try:
        arch = detect_system()
        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-{arch}"
        print("📥 Baixando cloudflared...")
        urllib.request.urlretrieve(url, "cloudflared")
        os.chmod("cloudflared", 0o755)
        print("✅ Cloudflared baixado como ./cloudflared")

        # Testar se funciona
        result = subprocess.run(['./cloudflared', '--version'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Cloudflared funcionando: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"❌ Erro no download: {e}")

    return False

def install_cloudflared_linux():
    """Instala cloudflared no Linux"""
    print("📦 Instalando cloudflared no Linux...")

    # Tentar apt primeiro (Ubuntu/Debian)
    try:
        subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)

        # Adicionar repositório Cloudflare
        subprocess.run([
            'sudo', 'mkdir', '-p', '--mode=0755', '/usr/share/keyrings'
        ], check=True, capture_output=True)

        subprocess.run([
            'sudo', 'wget', '-O', '/usr/share/keyrings/cloudflare-main.gpg',
            'https://pkg.cloudflare.com/cloudflare-main.gpg'
        ], check=True, capture_output=True)

        with open('/tmp/cloudflare.list', 'w') as f:
            f.write('deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main\n')

        subprocess.run([
            'sudo', 'mv', '/tmp/cloudflare.list', '/etc/apt/sources.list.d/cloudflared.list'
        ], check=True, capture_output=True)

        subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
        subprocess.run(['sudo', 'apt', 'install', 'cloudflared'], check=True, capture_output=True)

        print("✅ Cloudflared instalado via apt")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Apt falhou, tentando download direto...")

    # Download direto
    try:
        arch = detect_system()
        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-{arch}"
        print("📥 Baixando cloudflared...")
        urllib.request.urlretrieve(url, "cloudflared")
        os.chmod("cloudflared", 0o755)
        print("✅ Cloudflared baixado como ./cloudflared")

        # Testar se funciona
        result = subprocess.run(['./cloudflared', '--version'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Cloudflared funcionando: {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"❌ Erro no download: {e}")

    return False

def main():
    """Função principal"""
    print("🌐 DECTERUM - Setup Automático do Cloudflare Tunnel")
    print("="*50)

    # Verificar se já está instalado
    if check_cloudflared():
        print("✅ Cloudflared já está pronto!")
        return True

    print("⚠️ Cloudflared não encontrado. Instalando automaticamente...")

    # Detectar sistema
    system_type = detect_system()
    if not system_type:
        print("❌ Sistema operacional não suportado")
        return False

    print(f"🔍 Sistema detectado: {system_type}")

    # Instalar baseado no sistema
    success = False
    if "windows" in system_type:
        success = install_cloudflared_windows()
    elif "darwin" in system_type:
        success = install_cloudflared_macos()
    elif "linux" in system_type:
        success = install_cloudflared_linux()

    if success:
        print("\n✅ Cloudflared instalado com sucesso!")
        print("🚀 Agora você pode usar o Cloudflare Tunnel com DECTERUM")
        print("💡 Execute: python app.py para iniciar com tunnel automático")
    else:
        print("\n❌ Falha na instalação automática")
        print("💡 Instruções manuais:")
        if "windows" in system_type:
            print("   Windows: winget install Cloudflare.cloudflared")
        elif "darwin" in system_type:
            print("   macOS: brew install cloudflare/cloudflare/cloudflared")
        elif "linux" in system_type:
            print("   Linux: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared && chmod +x cloudflared")

    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Instalação cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)