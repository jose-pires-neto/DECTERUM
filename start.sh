#!/bin/bash
echo "🌐 Iniciando DECTERUM com DHT..."
echo "⏳ Aguarde a inicialização da rede P2P..."
export DECTERUM_DHT_ENABLED=true
python3 app.py
