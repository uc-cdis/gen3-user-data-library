import datetime
import uuid
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, ConfigDict, constr, Field, Extra
from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def is_dict(v: Any):
    assert isinstance(v, dict)
    return v


def is_nonempty(v: Any):
    assert v
    return v


class NonEmptyDict(Dict[str, Any]):
    @classmethod
    def __get_validators__(cls):
        yield is_dict
        yield is_nonempty


class UserListModel(BaseModel):
    version: int
    creator: constr(min_length=1)
    authz: Dict[str, Any]
    created_time: datetime
    updated_time: datetime
    name: constr(min_length=1)
    items: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class UserListResponseModel(BaseModel):
    lists: Dict[int, UserListModel]


class ItemToUpdateModel(BaseModel):
    name: constr(min_length=1)
    items: Dict[str, Any]
    model_config = ConfigDict(extra="forbid")


class UpdateItemsModel(BaseModel):
    lists: List[ItemToUpdateModel]


class IDToItems(BaseModel):
    UUID: Dict[str, Any]


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
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
        onupdate=datetime.datetime.now(datetime.timezone.utc),
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
