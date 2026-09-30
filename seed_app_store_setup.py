import asyncio
import motor.motor_asyncio
from datetime import datetime, timezone
import secrets
import hashlib

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_val = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return f"{salt}${hash_val}"

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, hash_val = hashed_password.split("$")
        check_val = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return secrets.compare_digest(hash_val, check_val)
    except Exception:
        return False

from app.core.config import settings
import os

async def main():
    MONGO_URL = os.getenv("MONGO_URL") or settings.MONGO_URL
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client.get_database("loukarver")

    # 1. Update Apple Reviewer Test Users
    reviewer_pass = "ReviewerPass2026!"
    hashed_pw = hash_password(reviewer_pass)
    
    u1 = await db.users.find_one({"email": "apple.review@aligned.app"})
    u2 = await db.users.find_one({"email": "partner.review@aligned.app"})
    
    from bson import ObjectId
    u1_id = u1["_id"] if u1 else ObjectId()
    u2_id = u2["_id"] if u2 else ObjectId()

    doc1 = {
        "_id": u1_id,
        "email": "apple.review@aligned.app",
        "password_hash": hashed_pw,
        "name": "Alex",
        "is_verified": True,
        "is_aligned": True,
        "partner": str(u2_id),
        "secret_key": "ALIGNED-APP1",
        "city_name": "Cupertino",
        "relationship_start_date": "01.01.2024",
        "is_long_distance": False,
        "is_deleted": False,
        "is_blocked": False,
        "is_hidden": False,
        "gender": "Non-binary"
    }

    doc2 = {
        "_id": u2_id,
        "email": "partner.review@aligned.app",
        "password_hash": hashed_pw,
        "name": "Taylor",
        "is_verified": True,
        "is_aligned": True,
        "partner": str(u1_id),
        "secret_key": "ALIGNED-APP2",
        "city_name": "Cupertino",
        "relationship_start_date": "01.01.2024",
        "is_long_distance": False,
        "is_deleted": False,
        "is_blocked": False,
        "is_hidden": False,
        "gender": "Non-binary"
    }

    await db.users.replace_one({"email": "apple.review@aligned.app"}, doc1, upsert=True)
    await db.users.replace_one({"email": "partner.review@aligned.app"}, doc2, upsert=True)

    test_u = await db.users.find_one({"email": "apple.review@aligned.app"})
    print("Apple Review User login verified:", verify_password(reviewer_pass, test_u["password_hash"]))

    # 2. Update Privacy Policy in MongoDB
    privacy_html = """
    <h2>1. Introduction</h2>
    <p>Aligned: Couples Journal ("Aligned", "we", "our", or "us") is dedicated to protecting your personal privacy. This Privacy Policy details how we collect, use, store, and safeguard your information when you use our mobile application and associated web services.</p>
    
    <h2>2. Information We Collect</h2>
    <p>To provide an intimate, synchronized, and engaging experience for two, we collect the following types of information:</p>
    <ul>
        <li><strong>Account Information:</strong> Your email address, encrypted password hash, chosen display name, gender, and relationship anniversary date.</li>
        <li><strong>Couple Interaction & Journal Content:</strong> Daily check-ins, mood reflections, private journal entries, shared vibe check responses, relationship milestones, date proposals, and memory notes.</li>
        <li><strong>Photos & Media:</strong> Photos you intentionally upload to shared memories or profiles (stored securely on Amazon Web Services S3).</li>
        <li><strong>Voice Notes & Audio:</strong> Audio clips recorded for partner voice notes when you grant microphone access.</li>
        <li><strong>Device & Notification Data:</strong> Device model, operating system version, and push notification tokens (managed securely via OneSignal) to alert you when your partner interacts with you.</li>
    </ul>

    <h2>3. How We Use Your Data</h2>
    <p>Your data is used solely to deliver the core functionality of Aligned, including:</p>
    <ul>
        <li>Pairing your account securely with your designated partner.</li>
        <li>Synchronizing shared reflections, answers, and date plans in real-time.</li>
        <li>Sending essential push notifications (e.g. partner replied, new daily question available).</li>
        <li>Ensuring account security, preventing unauthorized access, and maintaining service reliability.</li>
    </ul>
    <p><strong>We do NOT sell, rent, or monetize your personal data or private journal memories to advertisers or third parties.</strong></p>

    <h2>4. Data Storage and Security</h2>
    <p>We implement industry-standard encryption protocols (TLS/HTTPS in transit, AES encryption at rest via MongoDB Atlas and AWS S3). Authentication is managed through cryptographically signed JSON Web Tokens (JWT).</p>

    <h2>5. Account & Data Deletion (Apple Guideline 5.1.1(v))</h2>
    <p>You have full ownership of your data. You may delete your account and all associated personal data at any time:</p>
    <ul>
        <li><strong>Directly in the App:</strong> Navigate to Settings / Profile &rarr; Delete Account.</li>
        <li><strong>Via Support Request:</strong> Email us at <a href="mailto:mdsadimhasansourav@gmail.com">mdsadimhasansourav@gmail.com</a> with the subject "Data Deletion Request".</li>
    </ul>
    <p>Upon deletion, all your profile details, answers, memories, and media will be permanently removed from our active database.</p>

    <h2>6. Children's Privacy</h2>
    <p>Aligned is strictly designed for adults and couples aged 17 and older. We do not knowingly collect personal data from anyone under the age of 17.</p>

    <h2>7. Contact Information</h2>
    <p>For questions or privacy concerns regarding this Privacy Policy, please contact our Data Protection Officer:</p>
    <p><strong>Email:</strong> <a href="mailto:mdsadimhasansourav@gmail.com">mdsadimhasansourav@gmail.com</a></p>
    """

    # 3. Update Terms and Conditions in MongoDB
    terms_html = """
    <h2>1. Agreement to Terms</h2>
    <p>By downloading, accessing, or using Aligned: Couples Journal ("the App"), you agree to be bound by these Terms and Conditions. If you do not agree with any part of these Terms, you must discontinue using the App immediately.</p>

    <h2>2. Eligibility</h2>
    <p>You must be at least 17 years old to create an account and use the App. By using Aligned, you represent and warrant that you meet this age requirement.</p>

    <h2>3. User Accounts and Security</h2>
    <p>You are responsible for maintaining the confidentiality of your login credentials and for all activities that occur under your account. You agree to notify us immediately of any unauthorized use of your account.</p>

    <h2>4. Partner Pairing and Shared Content</h2>
    <p>Aligned enables two users to pair their accounts via a unique invitation code or QR code. When paired, content you submit (such as check-ins, journal threads, answers to vibe questions, and date ideas) becomes visible to your paired partner. You are solely responsible for ensuring you only pair with an individual you trust.</p>

    <h2>5. Acceptable Use and Content Standards</h2>
    <p>You agree not to use Aligned to:</p>
    <ul>
        <li>Upload, share, or transmit any content that is unlawful, harmful, abusive, harassing, defamatory, or obscene.</li>
        <li>Violate the intellectual property or privacy rights of any third party.</li>
        <li>Attempt to decompile, reverse-engineer, or compromise the security of the application or backend servers.</li>
    </ul>

    <h2>6. Termination</h2>
    <p>We reserve the right to suspend or terminate accounts that violate these Terms or engage in abusive behavior. You may terminate your account at any time via the in-app account deletion setting.</p>

    <h2>7. Disclaimer of Warranties and Limitation of Liability</h2>
    <p>The App is provided on an "AS IS" and "AS AVAILABLE" basis without warranties of any kind. Aligned is a relationship journaling and communication tool and is not a substitute for licensed couples therapy, marital counseling, or professional psychiatric advice.</p>

    <h2>8. Standard Apple End User License Agreement (EULA)</h2>
    <p>These terms incorporate and apply alongside Apple's standard Licensed Application End User License Agreement (EULA) accessible at <a href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/" target="_blank">Apple Standard EULA</a>.</p>

    <h2>9. Contact Us</h2>
    <p>For questions regarding these Terms, contact us at:</p>
    <p><strong>Email:</strong> <a href="mailto:mdsadimhasansourav@gmail.com">mdsadimhasansourav@gmail.com</a></p>
    """

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.legal_docs.update_one(
        {"doc_type": "privacy"},
        {"$set": {"content": privacy_html, "updated_at": now_iso}},
        upsert=True
    )
    print("Privacy Policy in MongoDB updated.")

    await db.legal_docs.update_one(
        {"doc_type": "terms"},
        {"$set": {"content": terms_html, "updated_at": now_iso}},
        upsert=True
    )
    print("Terms & Conditions in MongoDB updated.")

if __name__ == "__main__":
    asyncio.run(main())
