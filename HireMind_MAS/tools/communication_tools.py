"""
Outbound communication tools — email via SendGrid.

All functions return True on success and log errors on failure
without raising, so a failed notification never blocks the pipeline.
"""

import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config.settings import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, body: str) -> bool:
    message = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    try:
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
        success = response.status_code in (200, 202)
        if not success:
            logger.error("SendGrid returned %s for %s", response.status_code, to_email)
        return success
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def notify_shortlisted(candidate_name: str, candidate_email: str, job_title: str) -> bool:
    subject = f"HireMind — You've been shortlisted for {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Congratulations! After reviewing your profile, we'd like to move you forward "
        f"in the selection process for the {job_title} role.\n\n"
        f"Our team will be in touch shortly to schedule an interview.\n\n"
        f"Best regards,\nHireMind Recruiting"
    )
    return _send(candidate_email, subject, body)


def notify_rejected(candidate_name: str, candidate_email: str, job_title: str) -> bool:
    subject = f"HireMind — Update on your application for {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"Thank you for your interest in the {job_title} role. After careful review, "
        f"we will not be moving forward with your application at this time.\n\n"
        f"We encourage you to apply for future openings.\n\n"
        f"Best regards,\nHireMind Recruiting"
    )
    return _send(candidate_email, subject, body)


def send_interview_invite(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    scheduled_at: str,
    meeting_link: str,
) -> bool:
    subject = f"HireMind — Interview Invitation for {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"We'd like to invite you to an interview for the {job_title} role.\n\n"
        f"Date & Time : {scheduled_at}\n"
        f"Meeting Link: {meeting_link}\n\n"
        f"Please confirm your availability by replying to this email.\n\n"
        f"Best regards,\nHireMind Recruiting"
    )
    return _send(candidate_email, subject, body)


def notify_hired(candidate_name: str, candidate_email: str, job_title: str) -> bool:
    subject = f"HireMind — Offer for {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"We are thrilled to inform you that we would like to extend an offer for "
        f"the {job_title} position. Our team will follow up with the formal offer letter.\n\n"
        f"Congratulations!\n\n"
        f"Best regards,\nHireMind Recruiting"
    )
    return _send(candidate_email, subject, body)
