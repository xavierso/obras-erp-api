"""
Servicio unificado para envío de correos electrónicos.
Utiliza la API de Resend (https://resend.com).
"""
import os
import httpx
import logging

logger = logging.getLogger(__name__)

from app.config import settings

RESEND_API_KEY = settings.RESEND_API_KEY
FROM_EMAIL = settings.FROM_EMAIL

async def enviar_email(to_email: str, subject: str, html_content: str):
    if not RESEND_API_KEY:
        logger.warning(f"Simulando email a {to_email} (Asunto: {subject}). RESEND_API_KEY no configurado.")
        return

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": FROM_EMAIL,
        "to": to_email,
        "subject": subject,
        "html": html_content
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"Enviando email a {to_email}...")
            response = await client.post(url, headers=headers, json=data)
            print(f"Resend status code: {response.status_code}")
            print(f"Resend response: {response.text}")
            response.raise_for_status()
            logger.info(f"Email enviado a {to_email} con éxito.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error al enviar email: {e.response.text}")
            print(f"HTTPStatusError: {e.response.text}")
        except Exception as e:
            logger.error(f"Excepción al enviar email: {e}")
            print(f"Exception: {e}")
