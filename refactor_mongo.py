import os
import glob
import re

directory = 'app/services'
files = glob.glob(os.path.join(directory, '*.py'))

import_db = "from app.core.db import get_client, get_db\n"

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    
    # Check if this file has motor import
    if "from motor.motor_asyncio import AsyncIOMotorClient" in content:
        # We can remove the motor import if it's not used elsewhere, but let's just leave it to be safe,
        # or replace it with the app.core.db import if it's there.
        # Actually, let's just insert the new import after the motor one.
        if "from app.core.db" not in content:
            content = content.replace(
                "from motor.motor_asyncio import AsyncIOMotorClient", 
                "from motor.motor_asyncio import AsyncIOMotorClient\n" + import_db
            )
            
    # Replace the instantiation
    content = content.replace("self.client = AsyncIOMotorClient(settings.MONGO_URL)", "self.client = get_client()")
    content = content.replace("self.db = self.client[settings.MONGO_DB_NAME]", "self.db = get_db()")
    
    if original != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
