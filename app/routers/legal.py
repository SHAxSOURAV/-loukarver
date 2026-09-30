from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from app.services.legal import legal_service
from app.schemas.legal import LegalDocumentUpdate, LegalDocumentResponse
from app.routers.auth import get_current_user
import datetime

router = APIRouter(prefix="/legal", tags=["legal"])

CSS_STYLE = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        background-color: #fcfcfc;
    }
    h1, h2, h3 {
        color: #111;
        margin-top: 1.5em;
    }
    h1 {
        font-size: 2em;
        border-bottom: 2px solid #eaeaea;
        padding-bottom: 10px;
    }
    h2 {
        font-size: 1.5em;
        border-bottom: 1px solid #eaeaea;
        padding-bottom: 5px;
    }
    p {
        margin-bottom: 1em;
    }
    a {
        color: #0066cc;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    ul, ol {
        margin-bottom: 1em;
        padding-left: 20px;
    }
    li {
        margin-bottom: 0.5em;
    }
    .update-date {
        font-style: italic;
        color: #666;
        margin-bottom: 2em;
    }
    @media (prefers-color-scheme: dark) {
        body {
            background-color: #121212;
            color: #e0e0e0;
        }
        h1, h2, h3 {
            color: #ffffff;
            border-bottom-color: #333;
        }
        a {
            color: #4da6ff;
        }
        .update-date {
            color: #999;
        }
    }
</style>
"""

DEFAULT_PRIVACY = "<p>Welcome to Loukarver. Privacy policy coming soon...</p>"
DEFAULT_TERMS = "<p>Welcome to Loukarver. Terms and conditions coming soon...</p>"

@router.get("/api/docs/{doc_type}", response_model=LegalDocumentResponse)
async def get_legal_doc_api(doc_type: str):
    """API endpoint to get a legal document (JSON) for the Dashboard."""
    if doc_type not in ["privacy", "terms", "about"]:
        raise HTTPException(status_code=400, detail="Invalid doc_type. Use 'privacy', 'terms', or 'about'.")
        
    doc = await legal_service.get_document(doc_type)
    if not doc:
        # Return default if not exists
        default_content = ""
        if doc_type == "privacy":
            default_content = DEFAULT_PRIVACY
        elif doc_type == "terms":
            default_content = DEFAULT_TERMS
        else:
            default_content = "<p>About Us coming soon...</p>"
            
        return LegalDocumentResponse(
            id="default",
            doc_type=doc_type,
            content=default_content,
            updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
    return doc

@router.put("/api/docs/{doc_type}", response_model=LegalDocumentResponse)
async def update_legal_doc_api(doc_type: str, payload: LegalDocumentUpdate, current_user: dict = Depends(get_current_user)):
    """API endpoint to update a legal document (JSON) from the Dashboard. Requires Admin."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update legal documents.")
        
    if doc_type not in ["privacy", "terms", "about"]:
        raise HTTPException(status_code=400, detail="Invalid doc_type. Use 'privacy', 'terms', or 'about'.")
        
    doc = await legal_service.update_document(doc_type, payload)
    return doc

@router.get("/privacy", response_class=HTMLResponse)
async def get_privacy_policy():
    current_year = datetime.datetime.now().year
    
    doc = await legal_service.get_document("privacy")
    content = doc.get("content", DEFAULT_PRIVACY) if doc else DEFAULT_PRIVACY
    updated_at = doc.get("updated_at", "") if doc else ""
    
    date_str = ""
    if updated_at:
        try:
            dt = datetime.datetime.fromisoformat(updated_at)
            date_str = dt.strftime("%B %d, %Y")
        except:
            date_str = updated_at
    else:
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy - Aligned: Couples Journal</title>
        {CSS_STYLE}
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p class="update-date">Last Updated: {date_str}</p>
        
        {content}

        <p style="text-align: center; margin-top: 40px; color: #888;">&copy; {current_year} Aligned. All rights reserved.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/terms", response_class=HTMLResponse)
async def get_terms_and_conditions():
    current_year = datetime.datetime.now().year
    
    doc = await legal_service.get_document("terms")
    content = doc.get("content", DEFAULT_TERMS) if doc else DEFAULT_TERMS
    updated_at = doc.get("updated_at", "") if doc else ""
    
    date_str = ""
    if updated_at:
        try:
            dt = datetime.datetime.fromisoformat(updated_at)
            date_str = dt.strftime("%B %d, %Y")
        except:
            date_str = updated_at
    else:
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms and Conditions - Aligned: Couples Journal</title>
        {CSS_STYLE}
    </head>
    <body>
        <h1>Terms and Conditions</h1>
        <p class="update-date">Last Updated: {date_str}</p>

        {content}

        <p style="text-align: center; margin-top: 40px; color: #888;">&copy; {current_year} Aligned. All rights reserved.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/support", response_class=HTMLResponse)
async def get_support_page():
    current_year = datetime.datetime.now().year
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Support & Help Center - Aligned: Couples Journal</title>
        {CSS_STYLE}
    </head>
    <body>
        <h1>Aligned Support & Help Center</h1>
        <p class="update-date">Official Customer & Beta Tester Support</p>

        <p>Welcome to the <strong>Aligned: Couples Journal</strong> Support Center. We are here to help you get the most out of your shared rituals, daily connection prompts, and relationship journal.</p>

        <h2>How to Contact Us</h2>
        <p>If you have any questions, encounter a bug, or need assistance with your account, please reach out to our dedicated support team:</p>
        <ul>
            <li><strong>Email:</strong> <a href="mailto:mdsadimhasansourav@gmail.com">mdsadimhasansourav@gmail.com</a></li>
            <li><strong>Response Time:</strong> Within 24-48 business hours</li>
        </ul>

        <h2>Frequently Asked Questions</h2>
        <h3>How do I pair with my partner?</h3>
        <p>Once you register, share your 6-character Partner Alignment Code with your partner or scan their QR code in the app. Once they enter your code or scan the QR code, your accounts are synchronized instantly.</p>

        <h3>Is our data private?</h3>
        <p>Yes. Your responses, check-ins, vibe checks, and photos are exclusively shared between you and your paired partner. We do not sell your personal data to any third party.</p>

        <h3>How do I delete my account and data?</h3>
        <p>In accordance with Apple App Store Guideline 5.1.1(v), you can delete your account directly inside the app at any time by going to <strong>Settings / Profile &rarr; Delete Account</strong>. Alternatively, you can email us at <a href="mailto:mdsadimhasansourav@gmail.com">mdsadimhasansourav@gmail.com</a> with the subject "Data Deletion Request". All your private entries, photos, and messages will be permanently expunged from our database.</p>

        <p style="text-align: center; margin-top: 50px; color: #888;">&copy; {current_year} Aligned. All rights reserved.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


