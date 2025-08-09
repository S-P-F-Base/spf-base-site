import logging
import re

from requests import Session

from .config import Config


class MailControl:
    _session: Session = Session()
    RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    @classmethod
    def setup(cls) -> None:
        cls._session.headers.update({"Authorization": f"Bearer {Config.resend_api()}"})

    @classmethod
    def _validate_mail(cls, mail: str) -> bool:
        return bool(cls.RE.match(mail))

    @classmethod
    def send_mail(
        cls,
        to: list[str],
        subject: str,
        text: str,
        html: str | None = None,
    ) -> bool:
        recipients = [m for m in to if cls._validate_mail(m)]
        if not recipients:
            return False

        payload = {
            "from": "SPF Base <no-reply@spf-base.ru>",
            "to": recipients,
            "subject": subject,
            "text": text,
        }

        if html:
            payload["html"] = html

        response = cls._session.post(
            "https://api.resend.com/emails",
            json=payload,
        )

        if response.ok:
            logging.error(
                f"[MailControl] Failed to send mail: {response.status_code} - {response.text}"
            )
            return False

        return True
