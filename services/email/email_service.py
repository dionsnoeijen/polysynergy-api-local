from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import boto3
from fastapi import BackgroundTasks
from botocore.exceptions import ClientError
import logging

BASE_DIR = Path(__file__).resolve().parent.parent.parent
template_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"])
)

class EmailService:
    @staticmethod
    def send_invitation_email(to: str, portal_url: str, temporary_password: str, background_tasks: BackgroundTasks):
        subject = "Welcome to PolySynergy - Your Account is Ready"
        template = template_env.get_template("invitation_email.html")
        html_body = template.render(
            email=to,
            portal_url=portal_url,
            temporary_password=temporary_password
        )

        background_tasks.add_task(EmailService._send_via_ses, to, subject, html_body)

    @staticmethod
    def send_welcome_email(to: str, first_name: str, email: str, account_type: str, portal_url: str, background_tasks: BackgroundTasks):
        subject = "Welcome to PolySynergy!"
        template = template_env.get_template("welcome_email.html")
        html_body = template.render(
            first_name=first_name,
            email=email,
            account_type=account_type,
            portal_url=portal_url
        )

        background_tasks.add_task(EmailService._send_via_ses, to, subject, html_body)

    @staticmethod
    def send_admin_notification(admin_email: str, first_name: str, last_name: str, email: str, account_type: str, tenant_name: str, timestamp: str, background_tasks: BackgroundTasks):
        subject = "New Account Registration - PolySynergy"
        template = template_env.get_template("admin_new_account_notification.html")
        html_body = template.render(
            first_name=first_name,
            last_name=last_name,
            email=email,
            account_type=account_type,
            tenant_name=tenant_name,
            timestamp=timestamp
        )

        background_tasks.add_task(EmailService._send_via_ses, admin_email, subject, html_body)

    @staticmethod
    def send_feedback_email(
        user_email: str,
        message: str,
        timestamp: str,
        user_agent: str | None,
        background_tasks: BackgroundTasks
    ):
        """Send feedback email to admin"""
        admin_email = "dion@polysynergy.com"
        subject = f"User Feedback - PolySynergy ({user_email})"

        # Simple text-based email (no template needed for feedback)
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0ea5e9;">New Feedback Received</h2>

                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>From:</strong> {user_email}</p>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    {f'<p><strong>User Agent:</strong> {user_agent}</p>' if user_agent else ''}
                </div>

                <div style="background-color: #ffffff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #374151;">Message:</h3>
                    <p style="white-space: pre-wrap; color: #374151;">{message}</p>
                </div>

                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

                <p style="color: #6b7280; font-size: 12px;">
                    This feedback was sent via the PolySynergy Portal feedback form.
                </p>
            </body>
        </html>
        """

        # Send feedback email (user email is visible in the email body)
        background_tasks.add_task(
            EmailService._send_via_ses,
            admin_email,
            subject,
            html_body
        )

    @staticmethod
    def _send_via_ses(to: str, subject: str, html_body: str, reply_to: str = None):
        ses = boto3.client("ses", region_name="eu-central-1")
        try:
            email_params = {
                "Source": "PolySynergy <dion@polysynergy.com>",
                "Destination": {"ToAddresses": [to]},
                "Message": {
                    "Subject": {"Data": subject},
                    "Body": {
                        "Html": {"Data": html_body},
                    },
                },
            }

            # Add Reply-To header if provided
            if reply_to:
                email_params["ReplyToAddresses"] = [reply_to]

            ses.send_email(**email_params)
        except ClientError as e:
            logging.error(f"Failed to send email: {e.response['Error']['Message']}")
            raise  # Re-raise the exception so the caller knows it failed