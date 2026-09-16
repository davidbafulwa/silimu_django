import base64
import sys

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    """Envoi des e-mails via l'API REST de Brevo (clé API, pas de SMTP classique)."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not settings.BREVO_API_KEY:
            return 0
        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        sender_name, sender_email = self._parse_sender(message.from_email)
        html = next(
            (content for content, mimetype in getattr(message, 'alternatives', []) if mimetype == 'text/html'),
            None,
        )
        payload = {
            'sender': {'name': sender_name, 'email': sender_email},
            'to': [{'email': email} for email in message.to],
            'subject': message.subject,
            'textContent': message.body or '',
            'htmlContent': html or ' ',
        }
        attachments = self._build_attachments(getattr(message, 'attachments', []))
        if attachments:
            payload['attachment'] = attachments

        try:
            response = requests.post(
                'https://api.brevo.com/v3/smtp/email',
                json=payload,
                headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'},
                timeout=30,
            )
            if response.status_code not in (200, 201):
                print(
                    'Brevo HTTP %s: %s' % (response.status_code, response.text[:300]),
                    file=sys.stderr,
                )
            return response.status_code in (200, 201)
        except Exception as exc:
            if not self.fail_silently:
                raise exc

    @staticmethod
    def _parse_sender(from_email):
        from_email = (from_email or '').strip()
        if from_email.startswith('<'):
            return 'SILIMU', from_email.strip('<>')
        if ' <' in from_email and '>' in from_email:
            name, email = from_email.split(' <', 1)
            return name.strip(), email.rstrip('>')
        return 'SILIMU', from_email or settings.BREVO_SENDER_EMAIL

    @staticmethod
    def _build_attachments(attachments):
        result = []
        for attachment in attachments:
            name, content, mimetype = '', '', None
            if isinstance(attachment, (tuple, list)):
                name, content = attachment[0], attachment[1]
                if len(attachment) > 2:
                    mimetype = attachment[2]
            else:
                name = getattr(attachment, 'name', '')
                content = attachment.get_payload()
            if isinstance(content, str):
                content = content.encode('utf-8')
            item = {'name': name or 'piece_jointe', 'content': base64.b64encode(content).decode('ascii')}
            if mimetype:
                item['contentType'] = mimetype
            result.append(item)
        return result
