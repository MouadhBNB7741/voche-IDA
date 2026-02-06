import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_password_reset(email: str, reset_token: str):
        """Send password reset email with token link"""
        
        # Build reset URL
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
        
        # HTML Email Template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; 
                          color: white; text-decoration: none; border-radius: 5px; 
                          font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset your password for your VOCE account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="background: white; padding: 10px; border-radius: 5px; word-break: break-all;">
                        {reset_url}
                    </p>
                    <p><strong>⏰ This link will expire in 1 hour.</strong></p>
                    <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                </div>
                <div class="footer">
                    <p>VOCE System | Automated Email - Do Not Reply</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Password Reset Request
        
        We received a request to reset your password.
        
        Click this link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        """
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Reset Your Password - VOCE"
            message["From"] = settings.email_from
            message["To"] = email
            
            # Attach both plain and HTML versions
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send via SMTP
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()  # Secure connection
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
            
            logger.info(f"Password reset email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            raise Exception(f"Failed to send email: {str(e)}")
