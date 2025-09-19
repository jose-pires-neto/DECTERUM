#!/usr/bin/env python3
"""
DECTERUM - Teste Simples do Cloudflare
Script para testar e debugar a configuração do cloudflared
"""

import subprocess
import sys
import os
import time

def test_cloudflared_paths():
    """Testa diferentes caminhos do cloudflared"""
    print("🔍 Testando caminhos do cloudflared...\n")
    
    # Possíveis caminhos
    paths = [
        'cloudflared',
        'cloudflared.exe',
        r'C:\Program Files\cloudflared\cloudflared.exe',
        r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\\cloudflared.exe'),
        './cloudflared.exe',
        './cloudflared'
    ]
    
    working_paths = []
    
    for path in paths:
        try:
            print(f"  Testando: {path}")
            result = subprocess.run([path, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"  ✅ FUNCIONANDO: {path}")
                print(f"     Versão: {version}")
                working_paths.append(path)
            else:
                print(f"  ❌ Erro: {result.stderr.strip()}")
        except FileNotFoundError:
            print(f"  ❌ Arquivo não encontrado")
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        print()
    
    return working_paths

def test_environment():
    """Testa o ambiente do sistema"""
    print("🔧 Testando ambiente do sistema...\n")
    
    # Verificar PATH
    print("  PATH do sistema:")
    path_env = os.environ.get('PATH', '')
    for path in path_env.split(os.pathsep):
        if 'cloudflare' in path.lower():
            print(f"    ✅ {path}")
    
    # Verificar winget
    print("\n  Testando winget:")
    try:
        result = subprocess.run(['winget', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"    ✅ Winget disponível: {result.stdout.strip()}")
        else:
            print(f"    ❌ Erro no winget: {result.stderr}")
    except:
        print("    ❌ Winget não encontrado")
    
    # Verificar se cloudflared foi instalado via winget
    print("\n  Verificando instalação via winget:")
    try:
        result = subprocess.run(['winget', 'list', 'cloudflared'], 
                              capture_output=True, text=True, timeout=10)
        if 'cloudflared' in result.stdout.lower():
            print("    ✅ Cloudflared instalado via winget")
            print(f"    Detalhes:\n{result.stdout}")
        else:
            print("    ❌ Cloudflared não encontrado no winget")
    except:
        print("    ❌ Erro verificando winget list")

def test_simple_tunnel(cloudflared_path, port=8000):
    """Testa criação de túnel simples"""
    print(f"🌐 Testando túnel simples na porta {port}...\n")
    
    # Verificar se porta está em uso
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result != 0:
        print(f"  ⚠️ Porta {port} não está em uso")
        print("  💡 Inicie o DECTERUM primeiro: python app.py")
        return False
    
    print(f"  ✅ Porta {port} está em uso")
    
    # Tentar criar túnel
    print(f"  🚀 Iniciando túnel com: {cloudflared_path}")
    
    try:
        cmd = [cloudflared_path, 'tunnel', '--url', f'http://localhost:{port}']
        print(f"  Comando: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("  ⏳ Aguardando URL do túnel (15 segundos)...")
        
        start_time = time.time()
        tunnel_url = None
        
        while time.time() - start_time < 15:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"  ❌ Processo falhou:")
                print(f"     stdout: {stdout}")
                print(f"     stderr: {stderr}")
                return False
            
            line = process.stderr.readline()
            if line:
                print(f"    Log: {line.strip()}")
                if 'trycloudflare.com' in line:
                    parts = line.split()
                    for part in parts:
                        if 'trycloudflare.com' in part and part.startswith('https://'):
                            tunnel_url = part.strip()
                            print(f"  ✅ Túnel ativo: {tunnel_url}")
                            
                            # Testar túnel
                            print("  🧪 Testando túnel...")
                            try:
                                import requests
                                response = requests.get(f"{tunnel_url}/api/status", timeout=10)
                                if response.status_code == 200:
                                    print("  ✅ Túnel funcionando!")
                                    data = response.json()
                                    print(f"     Node ID: {data.get('node_id', 'N/A')}")
                                else:
                                    print(f"  ❌ Túnel retornou status {response.status_code}")
                            except Exception as e:
                                print(f"  ❌ Erro testando túnel: {e}")
                            
                            # Parar processo
                            process.terminate()
                            return tunnel_url
            
            time.sleep(0.1)
        
        print("  ⚠️ Timeout aguardando URL")
        process.terminate()
        return False
        
    except Exception as e:
        print(f"  ❌ Erro criando túnel: {e}")
        return False

def main():
    print("🌟 DECTERUM - Teste do Cloudflare Tunnel")
    print("=" * 50)
    
    # Testar ambiente
    test_environment()
    print("\n" + "="*50 + "\n")
    
    # Testar caminhos
    working_paths = test_cloudflared_paths()
    
    if not working_paths:
        print("❌ Nenhum cloudflared funcional encontrado!")
        print("\n💡 Soluções:")
        print("1. Reinicie o PowerShell e execute este script novamente")
        print("2. Instale manualmente: winget install Cloudflare.cloudflared")
        print("3. Baixe de: https://github.com/cloudflare/cloudflared/releases")
        return
    
    print(f"\n✅ {len(working_paths)} caminhos funcionais encontrados!")
    
    # Usar o primeiro caminho funcional
    cloudflared_path = working_paths[0]
    print(f"🎯 Usando: {cloudflared_path}")
    
    print("\n" + "="*50 + "\n")
    
    # Testar túnel
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    tunnel_url = test_simple_tunnel(cloudflared_path, port)
    
    if tunnel_url:
        print(f"\n🎉 Sucesso! Túnel configurado: {tunnel_url}")
        print("\n💡 Para usar no setup_cloudflare.py:")
        print(f"   cloudflared_path = '{cloudflared_path}'")
    else:
        print("\n❌ Não foi possível configurar túnel")
        print("\n💡 Certifique-se de que:")
        print(f"   1. DECTERUM está rodando na porta {port}")
        print("   2. Sua internet está funcionando")
        print("   3. Firewall não está bloqueando")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Teste cancelado")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()