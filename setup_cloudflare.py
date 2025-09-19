#!/usr/bin/env python3
"""
DECTERUM - Configuração Automática do Cloudflare Tunnel
Script para instalar e gerenciar cloudflared
"""

import subprocess
import time
import os
import sys
import json
import requests
import threading
from urllib.parse import urlparse

class CloudflareTunnelSetup:
    def __init__(self, port=8000):
        self.port = port
        self.tunnel_url = None
        self.tunnel_process = None
        self.is_running = False
        
    def check_cloudflared_installed(self):
        """Verifica se cloudflared está instalado em diferentes localizações"""
        
        # Possíveis caminhos do cloudflared
        possible_paths = [
            'cloudflared',  # PATH padrão
            'cloudflared.exe',  # Windows com extensão
            r'C:\Program Files\cloudflared\cloudflared.exe',  # Instalação padrão
            r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\\cloudflared.exe'),
            './cloudflared.exe',  # Local
            './cloudflared'  # Local Unix
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"✅ Cloudflared encontrado em: {path}")
                    return path
            except:
                continue
        
        # Tentar atualizar PATH e verificar novamente (Windows)
        if os.name == 'nt':
            try:
                print("🔄 Tentando atualizar PATH do Windows...")
                # Força atualização das variáveis de ambiente
                subprocess.run(['refreshenv'], shell=True, timeout=5)
                
                # Tenta novamente após refresh
                result = subprocess.run(['cloudflared', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print("✅ Cloudflared encontrado após atualização do PATH")
                    return 'cloudflared'
            except:
                pass
        
        print("❌ Cloudflared não encontrado em nenhum local")
        return None
    
    def install_cloudflared(self):
        """Instala cloudflared automaticamente"""
        print("📦 Instalando Cloudflared...")
        
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                return self._install_windows()
            elif system == "darwin":  # macOS
                return self._install_macos()
            elif system == "linux":
                return self._install_linux()
            else:
                print(f"❌ Sistema {system} não suportado para instalação automática")
                return False
                
        except Exception as e:
            print(f"❌ Erro na instalação: {e}")
            return False
    
    def _install_windows(self):
        """Instala no Windows com verificação melhorada"""
        print("🪟 Instalando para Windows...")
        
        try:
            # Primeiro, verificar se winget está disponível
            subprocess.run(['winget', '--version'], 
                          check=True, capture_output=True, timeout=5)
            
            print("⬇️ Baixando via Windows Package Manager...")
            result = subprocess.run([
                'winget', 'install', '--id', 'Cloudflare.cloudflared',
                '--accept-package-agreements', '--accept-source-agreements'
            ], timeout=120, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Instalação via winget concluída")
                
                # Aguardar um pouco para o sistema processar
                time.sleep(2)
                
                # Verificar se foi instalado
                cloudflared_path = self.check_cloudflared_installed()
                if cloudflared_path:
                    return cloudflared_path
                else:
                    print("⚠️ Instalação concluída mas comando não encontrado")
                    print("💡 Reinicie o PowerShell e tente novamente")
                    return False
            else:
                print(f"❌ Erro no winget: {result.stderr}")
                return self._install_windows_manual()
                
        except subprocess.CalledProcessError:
            print("❌ Winget não disponível, tentando instalação manual...")
            return self._install_windows_manual()
        except Exception as e:
            print(f"❌ Erro na instalação: {e}")
            return self._install_windows_manual()
    
    def _install_windows_manual(self):
        """Instalação manual para Windows"""
        print("📁 Fazendo download manual...")
        
        try:
            import urllib.request
            
            # URL do release mais recente
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            local_file = "cloudflared.exe"
            
            print(f"⬇️ Baixando de: {url}")
            urllib.request.urlretrieve(url, local_file)
            
            # Tornar executável
            os.chmod(local_file, 0o755)
            
            print(f"✅ Download concluído: {local_file}")
            return f"./{local_file}"
            
        except Exception as e:
            print(f"❌ Erro no download: {e}")
            return False
    
    def _install_macos(self):
        """Instala no macOS"""
        print("🍎 Instalando para macOS...")
        try:
            subprocess.run(['brew', 'install', 'cloudflare/cloudflare/cloudflared'], 
                          check=True, timeout=60)
            return 'cloudflared'
        except:
            print("❌ Homebrew não encontrado. Instale manualmente:")
            print("   brew install cloudflare/cloudflare/cloudflared")
            return False
    
    def _install_linux(self):
        """Instala no Linux"""
        print("🐧 Instalando para Linux...")
        try:
            # Tentar Ubuntu/Debian
            subprocess.run(['curl', '-L', '--output', 'cloudflared.deb', 
                          'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb'], 
                          check=True, timeout=30)
            subprocess.run(['sudo', 'dpkg', '-i', 'cloudflared.deb'], 
                          check=True, timeout=30)
            return 'cloudflared'
        except:
            try:
                # Download direto
                import urllib.request
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
                urllib.request.urlretrieve(url, "cloudflared")
                os.chmod("cloudflared", 0o755)
                print("📁 Baixado cloudflared")
                return "./cloudflared"
            except Exception as e:
                print(f"❌ Erro no download: {e}")
                return False
    
    def start_quick_tunnel(self, cloudflared_cmd):
        """Inicia túnel rápido (sem login)"""
        print(f"🌐 Configurando túnel para porta {self.port}...")
        
        try:
            cmd = [
                cloudflared_cmd, 'tunnel', 
                '--url', f'http://localhost:{self.port}',
                '--no-autoupdate'
            ]
            
            print(f"🚀 Executando: {' '.join(cmd)}")
            
            # Iniciar processo
            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            self.is_running = True
            
            # Aguardar URL do túnel
            return self._wait_for_tunnel_url()
            
        except Exception as e:
            print(f"❌ Erro ao iniciar túnel: {e}")
            return None
    
    def _wait_for_tunnel_url(self, timeout=30):
        """Aguarda e extrai URL do túnel"""
        print("⏳ Aguardando URL do túnel...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.tunnel_process.poll() is not None:
                # Processo morreu
                try:
                    stdout, stderr = self.tunnel_process.communicate(timeout=2)
                    print(f"❌ Processo falhou:")
                    print(f"   stdout: {stdout}")
                    print(f"   stderr: {stderr}")
                except:
                    pass
                return None
            
            # Ler stderr linha por linha
            try:
                line = self.tunnel_process.stderr.readline()
                if line:
                    print(f"   Log: {line.strip()}")
                    
                    # Procurar URL do tipo trycloudflare.com
                    if 'trycloudflare.com' in line and 'https://' in line:
                        # Extrair URL
                        parts = line.split()
                        for part in parts:
                            if 'trycloudflare.com' in part and part.startswith('https://'):
                                self.tunnel_url = part.strip()
                                print(f"✅ Túnel ativo: {self.tunnel_url}")
                                return self.tunnel_url
            except:
                pass
            
            time.sleep(0.5)
        
        print("⚠️ Timeout aguardando URL do túnel")
        return None
    
    def test_tunnel(self):
        """Testa se o túnel está funcionando"""
        if not self.tunnel_url:
            return False
            
        try:
            print(f"🧪 Testando túnel: {self.tunnel_url}")
            response = requests.get(f"{self.tunnel_url}/api/status", timeout=10)
            
            if response.status_code == 200:
                print("✅ Túnel funcionando corretamente!")
                return True
            else:
                print(f"❌ Túnel retornou status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro testando túnel: {e}")
            return False
    
    def stop_tunnel(self):
        """Para o túnel"""
        self.is_running = False
        
        if self.tunnel_process:
            try:
                print("🛑 Parando túnel...")
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
                print("✅ Túnel parado")
            except:
                try:
                    self.tunnel_process.kill()
                    print("⚠️ Túnel forçado a parar")
                except:
                    print("❌ Erro parando túnel")
            finally:
                self.tunnel_process = None
    
    def run_in_background(self):
        """Executa túnel em background"""
        def monitor():
            while self.is_running and self.tunnel_process:
                if self.tunnel_process.poll() is not None:
                    print("⚠️ Túnel parou inesperadamente")
                    break
                time.sleep(10)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def get_share_info(self):
        """Retorna informações para compartilhar"""
        if not self.tunnel_url:
            return None
            
        return {
            "tunnel_url": self.tunnel_url,
            "local_url": f"http://localhost:{self.port}",
            "instructions": [
                "Compartilhe este link com seus amigos:",
                f"🌐 {self.tunnel_url}",
                "",
                "Ou acesse localmente:",
                f"🏠 http://localhost:{self.port}"
            ]
        }

def main():
    print("🌟 DECTERUM - Configuração do Cloudflare Tunnel")
    print("=" * 50)
    
    # Obter porta
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    setup = CloudflareTunnelSetup(port)
    
    # Verificar se cloudflared está instalado
    cloudflared_path = setup.check_cloudflared_installed()
    
    if not cloudflared_path:
        print("\n❓ Cloudflared não encontrado. Opções:")
        print("1. Instalar automaticamente")
        print("2. Reiniciar PowerShell e tentar novamente")
        print("3. Instalar manualmente")
        
        response = input("Digite '1', '2' ou '3': ").strip()
        
        if response == '1':
            cloudflared_path = setup.install_cloudflared()
            if not cloudflared_path:
                print("\n❌ Não foi possível instalar automaticamente")
                print("💡 Soluções:")
                print("   1. Reinicie o PowerShell e execute: python setup_cloudflare.py")
                print("   2. Instale manualmente: winget install Cloudflare.cloudflared")
                print("   3. Execute este script em um novo terminal")
                sys.exit(1)
        elif response == '2':
            print("\n💡 Reinicie o PowerShell e execute:")
            print("   python setup_cloudflare.py")
            sys.exit(0)
        else:
            print("\n💡 Instale manualmente:")
            print("   Windows: winget install Cloudflare.cloudflared")
            print("   macOS:   brew install cloudflare/cloudflare/cloudflared")  
            print("   Linux:   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
            sys.exit(1)
    
    # Verificar se DECTERUM está rodando
    try:
        response = requests.get(f"http://localhost:{port}/api/status", timeout=5)
        if response.status_code != 200:
            print(f"⚠️ DECTERUM não está respondendo na porta {port}")
            print("💡 Certifique-se de que está rodando: python app.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ DECTERUM não está rodando na porta {port}")
        print("💡 Inicie primeiro: python app.py")
        sys.exit(1)
    
    # Iniciar túnel
    tunnel_url = setup.start_quick_tunnel(cloudflared_path)
    
    if tunnel_url:
        # Testar túnel
        if setup.test_tunnel():
            # Mostrar informações
            info = setup.get_share_info()
            if info:
                print("\n🎉 Túnel configurado com sucesso!")
                print("=" * 50)
                for line in info["instructions"]:
                    print(line)
                print("=" * 50)
                
                # Executar em background
                setup.run_in_background()
                
                try:
                    print("\n⌨️ Pressione Ctrl+C para parar o túnel")
                    while setup.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Parando túnel...")
                    setup.stop_tunnel()
        else:
            print("❌ Túnel não está respondendo corretamente")
            setup.stop_tunnel()
    else:
        print("❌ Não foi possível configurar o túnel")
        print("💡 Possíveis soluções:")
        print("   • Verifique se o DECTERUM está rodando na porta", port)
        print("   • Tente uma porta diferente")
        print("   • Verifique sua conexão com a internet")
        print("   • Reinicie o PowerShell e tente novamente")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Configuração cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)
