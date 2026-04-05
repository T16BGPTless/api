import requests
import pytest
from datetime import datetime

BASE_URL = "https://y1j7xv2ua6.execute-api.us-east-1.amazonaws.com/v1"

def test_practical_health():
    res = requests.get(f"{BASE_URL}/api/despatch/health")

    assert res.status_code == 200
    assert res.text == '"Service is operational"'