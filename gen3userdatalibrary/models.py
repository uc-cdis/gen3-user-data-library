import datetime
from typing import Dict

from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

ITEMS_JSON_SCHEMA_GENERIC = {
    "type": "object",
    "properties": {"type": {"type": "string"}},
    "required": ["type"],
}

ITEMS_JSON_SCHEMA_GEN3_GRAPHQL = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "schema_version": {"type": "string"},
        "data": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "variables": {"oneOf": [{"type": "object"}]},
            },
            "required": ["query", "variables"],
        },
    },
    "required": ["name", "type", "schema_version", "data"],
}


ITEMS_JSON_SCHEMA_DRS = {
    "type": "object",
    "properties": {"dataset_guid": {"type": "string"}, "type": {"type": "string"}},
    "required": ["dataset_guid", "type"],
}

BLACKLIST = {"id", "creator", "created_time"}

class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    creator = Column(String, nullable=False, index=True)
    authz = Column(JSON, nullable=False)

    name = Column(String, nullable=False)

    created_time = Column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_time = Column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    # see ITEMS_JSON_SCHEMA_* above for various schemas for different items here
    items = Column(JSON)

    __table_args__ = (UniqueConstraint("name", "creator", name="_name_creator_uc"),)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "version": self.version,
            "creator": self.creator,
            "authz": self.authz,
            "name": self.name,
            "created_time": (
                self.created_time.isoformat() if self.created_time else None
            ),
            "updated_time": (
                self.updated_time.isoformat() if self.updated_time else None
            ),
            "items": self.items,
        }
