#!/usr/bin/env python3
"""
Script para testar criação de post
"""

import requests
import json

url = "http://127.0.0.1:8000/api/feed/posts"
data = {
    "content": "Primeiro post após correção do retweets_count!",
    "post_type": "text"
}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Erro: {e}")