import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        with open('main.py', 'rb') as f:
            files = [('files', ('main.py', f, 'text/plain'))]
            data = {'rating': '5', 'text': 'nice'}
            r = await client.post('http://127.0.0.1:8002/dates/6a5484414e0fccc7f34157ac/review', data=data, files=files)
            print(r.status_code)
            print(r.json())

asyncio.run(main())
