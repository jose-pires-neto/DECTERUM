#!/usr/bin/env python3
"""
Script para criar um novo usuário no sistema
"""

from src.core.database import P2PDatabase
import uuid

print("Criando novo usuário...")

# Inicializar database
db = P2PDatabase()

# Verificar se já existe um usuário configurado
current_user_id = db.get_setting("current_user_id")
if current_user_id:
    user = db.get_user(current_user_id)
    if user:
        print(f"Usuário existente encontrado: {user['username']} (ID: {user['user_id']})")
        print("Usuário já configurado!")
        exit(0)

# Criar novo usuário
username = f"user_{uuid.uuid4().hex[:8]}"
user_id = db.create_user(username)
db.set_setting("current_user_id", user_id)

print(f"✓ Usuário criado: {username}")
print(f"✓ ID: {user_id}")
print(f"✓ Configurado como usuário atual")

# Verificar se funcionou
user = db.get_user(user_id)
if user:
    print(f"✓ Verificação: {user['username']} está ativo")
    print("✓ Sistema pronto para uso!")
else:
    print("✗ Erro: Usuário não foi criado corretamente")