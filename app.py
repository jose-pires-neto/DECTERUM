#!/usr/bin/env python3
"""
DECTERUM - Sistema P2P Descentralizado MODULAR
Entry point da aplicação
"""

import uvicorn
import logging
import sys
import os

# Adicionar src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.main import create_app

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Função principal da aplicação"""
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Porta inválida: {sys.argv[1]}, usando porta padrão 8000")

    logger.info(f"🚀 Iniciando DECTERUM na porta {port}")

    # Criar aplicação FastAPI
    app = create_app(port)

    # Iniciar servidor
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()