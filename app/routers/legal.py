from fastapi import APIRouter
from fastapi.responses import HTMLResponse
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

@router.get("/privacy", response_class=HTMLResponse)
async def get_privacy_policy():
    current_year = datetime.datetime.now().year
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy - Loukarver</title>
        {CSS_STYLE}
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p class="update-date">Last Updated: {current_date}</p>

        <p>Welcome to Loukarver ("we," "our," or "us"). We are committed to protecting your privacy and ensuring you have a positive experience on our mobile application (the "App"). This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use Loukarver.</p>
        
        <p>By using the App, you agree to the collection and use of information in accordance with this policy. If you do not agree with the terms of this privacy policy, please do not access the application.</p>

        <h2>1. Information We Collect</h2>
        <p>We may collect information about you in a variety of ways. The information we may collect via the App includes:</p>
        
        <h3>A. Personal Data</h3>
        <p>Demographic and other personally identifiable information (such as your name and email address) that you voluntarily give to us when choosing to participate in various activities related to the App, such as creating an account, sending messages, or creating shared memories.</p>
        
        <h3>B. User-Generated Content (UGC)</h3>
        <p>We collect and store the content you create, upload, or share on the App, including but not limited to:</p>
        <ul>
            <li>Photos, images, and audio/voice recordings uploaded to threads or milestones.</li>
            <li>Text content such as messages, prompts, journal entries, and check-ins.</li>
            <li>Responses to "Vibe Check" games, quizzes, and mood trackers.</li>
        </ul>

        <h3>C. Location Information</h3>
        <p>To enable certain core features, such as adding "Map Pins" (e.g., hometowns, places you've been together, or bucket list locations), we may request access or permission to and track location-based information from your mobile device, either continuously or while you are using the App.</p>
        
        <h3>D. Derivative Data & Analytics</h3>
        <p>Information our servers automatically collect when you access the App, such as your native actions that are integral to the App, including interacting with your partner, clicking on buttons, and tracking application stability and crashes to improve performance.</p>

        <h2>2. How We Use Your Information</h2>
        <p>Having accurate information about you permits us to provide you with a smooth, efficient, and customized experience. Specifically, we may use information collected about you via the App to:</p>
        <ul>
            <li>Create and manage your account and facilitate connections with your partner.</li>
            <li>Provide app functionality such as streaks, threads, relationship milestones, and location mapping.</li>
            <li>Process and securely store your shared photos, voice notes, and text data.</li>
            <li>Send push notifications regarding account activity, partner updates, or reminders.</li>
            <li>Monitor and analyze usage and trends to improve your experience with the App.</li>
            <li>Prevent fraudulent transactions, monitor against theft, and protect against criminal activity.</li>
        </ul>

        <h2>3. Disclosure of Your Information</h2>
        <p>Your information is primarily shared with your connected partner within the App. We may share information we have collected about you in certain situations:</p>
        
        <h3>A. By Law or to Protect Rights</h3>
        <p>If we believe the release of information about you is necessary to respond to legal process, to investigate or remedy potential violations of our policies, or to protect the rights, property, and safety of others, we may share your information as permitted or required by any applicable law, rule, or regulation.</p>
        
        <h3>B. Third-Party Service Providers</h3>
        <p>We may share your information with third parties that perform services for us or on our behalf, including data analysis, email delivery, hosting services, customer service, and push notifications.</p>

        <h2>4. Data Retention & Deletion</h2>
        <p>We will only retain your personal information for as long as necessary to fulfill the purposes we collected it for, including for the purposes of satisfying any legal, accounting, or reporting requirements.</p>
        <p><strong>Account Deletion:</strong> You can request the deletion of your account and associated personal data at any time by contacting us at <strong>support@loukarver.com</strong> or using the in-app deletion feature (if available). Upon your request to terminate your account, we will deactivate or delete your account and information from our active databases.</p>

        <h2>5. Security of Your Information</h2>
        <p>We use administrative, technical, and physical security measures to help protect your personal information. While we have taken reasonable steps to secure the personal information you provide to us, please be aware that despite our efforts, no security measures are perfect or impenetrable, and no method of data transmission can be guaranteed against any interception or other type of misuse.</p>

        <h2>6. Policy for Children</h2>
        <p>We do not knowingly solicit information from or market to children under the age of 13. If you become aware of any data we have collected from children under age 13, please contact us using the contact information provided below.</p>

        <h2>7. Changes to This Privacy Policy</h2>
        <p>We may update this Privacy Policy from time to time in order to reflect, for example, changes to our practices or for other operational, legal, or regulatory reasons. We will notify you of any changes by updating the "Last Updated" date of this Privacy Policy. You are encouraged to periodically review this Privacy Policy to stay informed of updates.</p>

        <h2>8. Contact Us</h2>
        <p>If you have questions or comments about this Privacy Policy, please contact us at:</p>
        <p><strong>Email:</strong> support@loukarver.com</p>

        <p style="text-align: center; margin-top: 40px; color: #888;">&copy; {current_year} Loukarver. All rights reserved.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/terms", response_class=HTMLResponse)
async def get_terms_and_conditions():
    current_year = datetime.datetime.now().year
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms and Conditions - Loukarver</title>
        {CSS_STYLE}
    </head>
    <body>
        <h1>Terms and Conditions</h1>
        <p class="update-date">Last Updated: {current_date}</p>

        <p>Welcome to Loukarver ("we," "our," or "us"). These Terms and Conditions govern your use of the Loukarver mobile application (the "App"). By downloading, installing, or using the App, you agree to be bound by these Terms.</p>

        <p>If you do not agree to these Terms, please do not use the App.</p>

        <h2>1. Use of the App</h2>
        <p>Loukarver is designed to help couples connect through shared milestones, photos, locations, and interactive elements ("Vibe Checks," "Streaks").</p>
        <ul>
            <li><strong>Eligibility:</strong> You must be at least 13 years old to use the App.</li>
            <li><strong>Account Creation:</strong> You must provide accurate, current, and complete information during the registration process and keep your account information up-to-date.</li>
            <li><strong>Security:</strong> You are responsible for safeguarding the password that you use to access the App and for any activities or actions under your password.</li>
        </ul>

        <h2>2. User-Generated Content (UGC)</h2>
        <p>The App allows you to upload, submit, store, send or receive content, including photos, location data, audio recordings, and text ("User Content").</p>
        
        <h3>A. Ownership and License</h3>
        <p>You retain ownership of any intellectual property rights that you hold in your User Content. When you upload or otherwise submit content to our App, you give Loukarver a worldwide license to use, host, store, reproduce, modify, create derivative works, communicate, publish, and distribute such content solely for the purpose of operating, promoting, and improving our App, and to provide the App to you and your connected partner.</p>
        
        <h3>B. Prohibited Content</h3>
        <p>You agree not to post, upload, publish, submit, or transmit any User Content that:</p>
        <ul>
            <li>Infringes, misappropriates, or violates a third party's patent, copyright, trademark, trade secret, moral rights, or other intellectual property rights.</li>
            <li>Violates, or encourages any conduct that would violate, any applicable law or regulation or would give rise to civil liability.</li>
            <li>Is fraudulent, false, misleading, or deceptive.</li>
            <li>Is defamatory, obscene, pornographic, vulgar, or offensive.</li>
            <li>Promotes discrimination, bigotry, racism, hatred, harassment, or harm against any individual or group.</li>
            <li>Is violent or threatening or promotes violence or actions that are threatening to any person or entity.</li>
        </ul>
        <p><strong>We reserve the right to review, monitor, and remove User Content at any time, without prior notice, at our sole discretion, if it violates these Terms.</strong></p>

        <h3>C. Apple and Google Compliance for UGC</h3>
        <p>In accordance with Apple App Store and Google Play Store policies for apps containing user-generated content:</p>
        <ul>
            <li>We enforce a zero-tolerance policy for objectionable content and abusive users.</li>
            <li>Users have the ability to flag or report objectionable content and abusive users.</li>
            <li>We will act on objectionable content reports within 24 hours by removing the content and ejecting the user who provided the offending content.</li>
        </ul>

        <h2>3. Subscriptions and Purchases (if applicable)</h2>
        <p>Some parts of the App may be billed on a subscription basis ("Subscription(s)"). You will be billed in advance on a recurring and periodic basis. Depending on the platform, your subscription is managed by the Apple App Store or Google Play Store.</p>
        <p>Cancellation and refund policies are governed by the respective store from which you purchased the subscription.</p>

        <h2>4. Prohibited Conduct</h2>
        <p>You agree not to do any of the following:</p>
        <ul>
            <li>Use the App in any way that violates any applicable national, regional, or local law.</li>
            <li>Attempt to probe, scan, or test the vulnerability of any Loukarver system or network or breach any security or authentication measures.</li>
            <li>Interfere with, or attempt to interfere with, the access of any user, host, or network, including sending a virus, overloading, flooding, spamming, or mail-bombing the App.</li>
        </ul>

        <h2>5. Termination</h2>
        <p>We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.</p>
        <p>Upon termination, your right to use the App will immediately cease. If you wish to terminate your account, you may simply discontinue using the App or request account deletion via <strong>support@loukarver.com</strong>.</p>

        <h2>6. Limitation of Liability</h2>
        <p>In no event shall Loukarver, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from (i) your access to or use of or inability to access or use the App; (ii) any conduct or content of any third party on the App; (iii) any content obtained from the App; and (iv) unauthorized access, use or alteration of your transmissions or content.</p>

        <h2>7. Disclaimer</h2>
        <p>Your use of the App is at your sole risk. The App is provided on an "AS IS" and "AS AVAILABLE" basis. The App is provided without warranties of any kind, whether express or implied.</p>

        <h2>8. Changes to Terms</h2>
        <p>We reserve the right, at our sole discretion, to modify or replace these Terms at any time. By continuing to access or use our App after those revisions become effective, you agree to be bound by the revised terms.</p>

        <h2>9. Contact Us</h2>
        <p>If you have any questions about these Terms, please contact us at:</p>
        <p><strong>Email:</strong> support@loukarver.com</p>

        <p style="text-align: center; margin-top: 40px; color: #888;">&copy; {current_year} Loukarver. All rights reserved.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
