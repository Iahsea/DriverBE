#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/user/LAB')

from dotenv import load_dotenv
load_dotenv()

import requests
import json

user_id = "85e042c5445b4ae39d856dc2f49801a0"
url = f"http://127.0.0.1:8000/api/v1/auth/users/{user_id}"

print(f"Testing endpoint: {url}")
print("-" * 50)

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
