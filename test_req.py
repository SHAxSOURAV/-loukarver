import urllib.request, urllib.error, json
req = urllib.request.Request('http://127.0.0.1:8002/thread/voice_base64', data=json.dumps({'file_base64': 'test', 'filename': 'a.m4a', 'content_type': 'audio/m4a', 'category': 'Voice', 'timezone': 'UTC'}).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode('utf-8'))
