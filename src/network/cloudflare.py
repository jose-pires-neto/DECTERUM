import os
import subprocess
import threading
import logging

logger = logging.getLogger(__name__)


class CloudflareManager:
    """Gerenciador do Cloudflare Tunnel"""

    def __init__(self, port: int):
        self.port = port
        self.tunnel_url = None
        self.tunnel_process = None

    def check_cloudflared_installed(self):
        """Verifica se cloudflared está instalado"""
        possible_paths = [
            'cloudflared',
            'cloudflared.exe',
            r'C:\Program Files\cloudflared\cloudflared.exe',
            r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            os.path.expanduser(
                '~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\\cloudflared.exe'),
            './cloudflared.exe',
            './cloudflared'
        ]

        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    logger.info(f"✅ Cloudflared encontrado em: {path}")
                    return path
            except:
                continue

        logger.warning("⚠️ Cloudflared não encontrado.")
        return None

    def setup_tunnel(self):
        """Configura e inicia o túnel Cloudflare"""
        cloudflared_path = self.check_cloudflared_installed()
        if not cloudflared_path:
            logger.warning("Cloudflare Tunnel não disponível - apenas acesso local")
            return None

        try:
            logger.info("🌐 Configurando túnel Cloudflare...")
            cmd = [
                cloudflared_path, 'tunnel',
                '--url', f'http://localhost:{self.port}',
                '--no-autoupdate'
            ]

            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Lê a saída do processo para obter URL
            tunnel_url_holder = {'url': None}

            def read_output(process, holder):
                try:
                    while True:
                        line = process.stderr.readline()
                        if not line:
                            break
                        logger.debug(f"Cloudflare: {line.strip()}")
                        if 'trycloudflare.com' in line:
                            parts = line.split()
                            for part in parts:
                                if 'trycloudflare.com' in part and part.startswith('https://'):
                                    holder['url'] = part.replace('|', '').strip()
                                    logger.info(f"✅ Túnel Cloudflare ativo: {holder['url']}")
                                    return
                except Exception as e:
                    logger.error(f"Erro lendo saída do Cloudflare: {e}")

            output_thread = threading.Thread(target=read_output, args=(self.tunnel_process, tunnel_url_holder),
                                             daemon=True)
            output_thread.start()
            output_thread.join(timeout=30)

            if tunnel_url_holder['url']:
                self.tunnel_url = tunnel_url_holder['url']
                return self.tunnel_url

            logger.warning("⚠️ Timeout configurando túnel Cloudflare")
            self.stop_tunnel()
            return None

        except Exception as e:
            logger.error(f"Erro configurando túnel: {e}")
            return None

    def stop_tunnel(self):
        """Para o túnel"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                logger.info("🛑 Túnel Cloudflare parado")
                self.tunnel_process.wait(timeout=10)
            except Exception as e:
                logger.error(f"Erro parando túnel: {e}")
                try:
                    self.tunnel_process.kill()
                except:
                    pass
            finally:
                self.tunnel_process = None
                self.tunnel_url = None