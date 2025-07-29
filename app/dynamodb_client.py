"""DynamoDB Client

DynamoDBのテーブル操作を行うクラス (pynamodb版)
"""

import logging
from typing import Any

from models import Settings
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model

logger = logging.getLogger(__name__)


class CallParamsTable(Model):
    class Meta:
        table_name = ""
        region = ""
        host = ""

    id = UnicodeAttribute(hash_key=True)
    call_params = MapAttribute()
    to_list = ListAttribute(null=True)
    created_at = UTCDateTimeAttribute()


class DynamoDBClient:
    """DynamoDBの操作を行うクラス (pynamodb版)."""

    def __init__(self, settings: Settings):
        CallParamsTable.Meta.table_name = settings.dynamodb_table_name
        CallParamsTable.Meta.region = settings.dynamodb_region
        CallParamsTable.Meta.host = settings.dynamodb_host or None
        self.model = CallParamsTable
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self) -> bool:
        """Create table if not exists."""
        try:
            if not CallParamsTable.exists():
                logger.info("create_table_if_not_exists: table not exists")
                CallParamsTable.create_table(
                    read_capacity_units=3, write_capacity_units=3, wait=True
                )
                logger.info("create_table_if_not_exists: table created")
            else:
                logger.info("create_table_if_not_exists: table already exists")
        except Exception as e:
            logger.error(f"create_table_if_not_exists error: {e}")
            return False
        return True

    def put_item(self, data: dict[str, Any]) -> bool:
        try:
            self.model(**data).save()
            logger.info(f"put_item success: {data}")
            return True
        except Exception as e:
            logger.error(f"put_item error: {e}")
            return False

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        try:
            item = self.model.get(item_id)
            logger.info(f"get_item success: {item_id}: {item}")
            return item
        except DoesNotExist:
            logger.info(f"get_item not found: {item_id}")
            return None
        except Exception as e:
            logger.error(f"get_item error: {e}")
            return None

    def update_item(
        self, item_id: str, data: dict[str, Any], merge: bool = True
    ) -> bool:
        print(f"update_item: {item_id} {data}")
        try:
            item = self.model.get(item_id)
            print(f"item: {item}")
            print("ok")
            for key, value in data.items():
                setattr(item, key, value)
            item.save()
            logger.info(f"Update item: {item_id} {data}")
            return True
        except DoesNotExist:
            logger.info(f"Item not found: {item_id} {data}")
            return self.put_item(data)
        except Exception as e:
            logger.error(f"Update item error: {item_id} {data} {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        try:
            item = self.model.get(item_id)
            item.delete()
            logger.info(f"Delete item: {item_id}")
            return True
        except DoesNotExist:
            logger.info(f"Delete item not found: {item_id}")
            return False
        except Exception as e:
            logger.error(f"Delete item error: {item_id} {e}")
            return False
