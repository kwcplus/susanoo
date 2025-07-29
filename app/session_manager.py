import random
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from dynamodb_client import DynamoDBClient
from models import CallParams, Settings


class SessionManager:
    def __init__(self, settings: Settings):
        self.db = DynamoDBClient(settings)

    def create(self, call_params: CallParams):
        session_id = str(uuid.uuid4())
        data = {
            "id": session_id,
            "call_params": call_params.model_dump(),
            "to_list": self.create_to_list(call_params),
            "created_at": self.created_at(),
        }
        if not self.db.put_item(data):
            raise ValueError(f"DynamoDB put_item error: {data}")
        return session_id

    def create_to_list(self, call_params: CallParams):
        to_list = []
        numbers = call_params.to.split(",")
        if call_params.round_robin:
            random.shuffle(numbers)
        for _ in range(call_params.loop):
            to_list.extend(numbers)
        return to_list

    def created_at(self):
        return datetime.now(ZoneInfo("Asia/Tokyo"))

    def delete(self, session_id: str):
        if not self.db.delete_item(session_id):
            raise ValueError(f"DynamoDB delete_item error: {session_id}")
        return session_id

    def read(self, item_id: str):
        item = self.db.get_item(item_id)
        if not item:
            raise ValueError(f"session not found: {item_id}")
        return item

    def update(self, session_id: str, to_list: list):
        if not self.db.update_item(session_id, {"to_list": to_list}):
            raise ValueError(f"DynamoDB update_item error: {session_id} {to_list}")
        return session_id
