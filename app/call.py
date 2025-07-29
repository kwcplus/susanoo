import base64
import logging
import re

from models import Settings
from vonage import Auth, Vonage
from vonage_voice import CreateCallRequest

logger = logging.getLogger(__name__)


class Call:
    def __init__(self, settings: Settings):
        self.client = Vonage(
            Auth(
                application_id=settings.vonage_application_id,
                private_key=base64.b64decode(settings.vonage_private_key),
            )
        )

    def create(self, to: str, from_: str, ncco: list, event_url: list):
        call_request = CreateCallRequest(
            to=[{"type": "phone", "number": to}],
            from_={"type": "phone", "number": from_},
            ncco=ncco,
            event_url=[event_url],
        )
        return self.client.voice.create_call(call_request)

    @staticmethod
    def clean_number(number: str) -> str:
        return re.sub(r"[-+\s\(\)]", "", number)

    @staticmethod
    def to_e164(number: str) -> str:
        e164 = Call.clean_number(number)
        if e164.startswith("0"):
            e164 = "81" + e164[1:]
        return e164

    @staticmethod
    def validate_number(number: str) -> bool:
        cleaned = Call.clean_number(number)
        return bool(re.match(r"^\d{10,12}$", cleaned))
