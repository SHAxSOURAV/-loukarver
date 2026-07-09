import asyncio
import httpx

async def test_flow():
    base_url = 'http://localhost:8002'
    
    # Login x3
    async with httpx.AsyncClient() as client:
        res3 = await client.post(f'{base_url}/auth/signin', json={'email': 'x3@yopmail.com', 'password': 'Secure123'})
        token3 = res3.json()['access_token']
        headers3 = {'Authorization': f'Bearer {token3}'}
        
        # Get notifications for x3
        notifs_res = await client.get(f'{base_url}/notifications/?types=Vibe%20System', headers=headers3)
        notifs = notifs_res.json().get('data', [])
        
        print('\n--- x3 VIBE SYSTEM NOTIFICATIONS ---')
        for n in notifs:
            print(f"Title: {n.get('title')}")
            print(f"Message: {n.get('message')}")
            print(f"Type: {n.get('type')}")
            print('---')

asyncio.run(test_flow())
