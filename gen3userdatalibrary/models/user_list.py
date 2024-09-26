import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserListModel(BaseModel):
    version: int
    creator: str
    authz: Dict[str, Any]
    name: str
    created_time: datetime
    updated_time: datetime
    items: Optional[Dict[str, Any]] = None


class UserListResponseModel(BaseModel):
    lists: Dict[int, UserListModel]


class RequestedUserListModel(BaseModel):
    name: str
    items: Optional[Dict] = {}  # Nested items


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
        nullable=False)
    updated_time = Column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False)

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
            "created_time": (self.created_time.isoformat() if self.created_time else None),
            "updated_time": (self.updated_time.isoformat() if self.updated_time else None),
            "items": self.items}
