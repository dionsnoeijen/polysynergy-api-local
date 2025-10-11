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
    def _send_via_ses(to: str, subject: str, html_body: str):
        ses = boto3.client("ses", region_name="eu-central-1")
        try:
            ses.send_email(
                Source="no-reply@polysynergy.com",
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Html": {"Data": html_body},
                    },
                },
            )
        except ClientError as e:
            logging.error(f"Failed to send email: {e.response['Error']['Message']}")