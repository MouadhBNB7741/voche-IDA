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
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 0; }}
                .wrapper {{ padding: 40px 20px; text-align: center; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); text-align: left; border: 1px solid #e2e8f0; }}
                .header {{ padding: 32px; text-align: center; border-bottom: 1px solid #f1f5f9; }}
                .logo-text {{ color: #10b981; font-weight: 800; font-size: 28px; letter-spacing: -0.5px; margin: 0; }}
                .content {{ padding: 40px 32px; }}
                .content p {{ margin: 0 0 20px 0; font-size: 16px; color: #475569; }}
                .button-container {{ text-align: center; margin: 32px 0; }}
                .button {{ display: inline-block; padding: 14px 32px; background-color: #10b981; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; transition: background-color 0.2s; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2); }}
                .link-box {{ background: #f8fafc; border: 1px dashed #cbd5e1; padding: 16px; border-radius: 8px; font-size: 14px; word-break: break-all; color: #64748b; text-align: center; margin-bottom: 24px; }}
                .warning {{ font-size: 14px; color: #f59e0b; background: #fffbeb; padding: 12px 16px; border-radius: 8px; margin-bottom: 0; display: inline-block; }}
                .footer {{ padding: 24px; text-align: center; background: #f8fafc; border-top: 1px solid #f1f5f9; color: #94a3b8; font-size: 13px; }}
            </style>
        </head>
        <body>
            <div class="wrapper">
                <div class="container">
                    <div class="header">
                        <div class="logo-text">voche</div>
                    </div>
                    <div class="content">
                        <h2 style="margin-top: 0; color: #0f172a; font-size: 20px; font-weight: 700;">Password Reset Request</h2>
                        <p>Hello,</p>
                        <p>We received a secure request to reset the password for your Voche account. If you initiated this request, you can set a new password by clicking the button below.</p>
                        
                        <div class="button-container">
                            <a href="{reset_url}" class="button">Reset Password</a>
                        </div>
                        
                        <p style="font-size: 14px; margin-bottom: 8px;">Or copy and paste this link into your browser:</p>
                        <div class="link-box">
                            {reset_url}
                        </div>
                        
                        <div style="text-align: center;">
                            <span class="warning">⏱️ This secure link will expire in 1 hour.</span>
                        </div>
                        
                        <p style="margin-top: 24px; font-size: 14px; color: #64748b;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                    </div>
                    <div class="footer">
                        &copy; Voche Health. All rights reserved.<br>
                        Automated Security Email - Do Not Reply
                    </div>
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
            message["Subject"] = "Reset Your Password - voche"
            message["From"] = settings.email_from or settings.smtp_user
            message["To"] = email
            
            # Attach both plain and HTML versions
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send via SMTP
            smtp_method = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
            logger.info(f"Connecting to SMTP server {settings.smtp_host}:{settings.smtp_port}...")
            
            with smtp_method(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_port != 465:
                    server.starttls()  # Secure connection for 587
                
                logger.info(f"Attempting SMTP login for {settings.smtp_user}...")
                server.login(settings.smtp_user, settings.smtp_password)
                
                logger.info(f"Sending email to {email}...")
                server.send_message(message)
            
            logger.info(f"✅ Password reset email successfully sent to {email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error(f"❌ SMTP Authentication failed for {settings.smtp_user}. Check your credentials.")
            raise Exception("Email authentication failed.")
        except Exception as e:
            logger.error(f"❌ Failed to send email to {email}: {str(e)}")
            raise Exception(f"Failed to send email: {str(e)}")
