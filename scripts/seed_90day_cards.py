import asyncio
import csv
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Make sure this matches your local MongoDB or use env var
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "loukarver"

async def seed_cards():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db["vibe_90day_cards"]

    # Clear existing collection
    await collection.delete_many({})

    csv_path = r"C:\Users\mdsad\Documents\loukarver\Data\vibe-check-cards - final 270.csv"
    
    cards = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cards.append({
                "day": int(row["day"]),
                "slot": int(row["slot"]),
                "card_id": row["card_id"],
                "category": row["category"],
                "depth": row["depth"],
                "option_a": row["option_a"],
                "option_b": row["option_b"],
                "is_anchor": row["anchor"].strip().lower() == 'true'
            })
    
    if cards:
        await collection.insert_many(cards)
        print(f"Successfully seeded {len(cards)} cards!")
        
        # Create an index for quick lookup
        await collection.create_index([("day", 1), ("slot", 1)], unique=True)
        await collection.create_index("card_id", unique=True)
    else:
        print("No cards found in the CSV.")

if __name__ == "__main__":
    asyncio.run(seed_cards())
