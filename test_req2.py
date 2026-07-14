import urllib.request, urllib.error, json
from app.services.auth import create_access_token

token = create_access_token({"user_id": "test_id", "email": "test@test.com"})

req = urllib.request.Request(
    'http://127.0.0.1:8002/thread/voice_base64', 
    data=json.dumps({
        'file_base64': 'test', 
        'filename': 'a.m4a', 
        'content_type': 'audio/m4a', 
        'category': 'Voice', 
        'timezone': 'UTC'
    }).encode('utf-8'), 
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
)

try:
    res = urllib.request.urlopen(req)
    print("Success:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"Error {e.code}:", e.read().decode('utf-8'))
