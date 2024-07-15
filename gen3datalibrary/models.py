import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

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
    "properties": {"dataset_guid": {"type": "string"}},
    "required": ["dataset_guid"],
}


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    creator = Column(String, nullable=False, index=True)
    authz = Column(JSON, nullable=False)

    name = Column(String, nullable=False)

    created_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # see ITEMS_JSON_SCHEMA_* above for various schemas for different items here
    items = Column(JSON)
