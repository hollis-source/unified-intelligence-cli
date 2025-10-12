#!/usr/bin/env python3
import requests
from dotenv import load_dotenv
import os

load_dotenv()

password = os.getenv("PB_DB_PASSWORD")
print(f"Password from .env: {repr(password)}")
print(f"Password length: {len(password)}")

url = "http://localhost:8001/sql"
auth = ("root", password)
headers = {
    "Surreal-NS": "project_builder",
    "Surreal-DB": "production",
    "Accept": "application/json",
}
query = "USE NS project_builder; USE DB production; SELECT * FROM projects LIMIT 1;"

response = requests.post(url, data=query, auth=auth, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
