import datetime
import uuid
from typing import Dict, Any, List

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSONB, Column, DateTime, Integer, String, UniqueConstraint, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NonEmptyDict(Dict[str, Any]):
    @classmethod
    def __get_validators__(cls):
        yield is_dict
        yield is_nonempty


class UserListModel(BaseModel):
    version: int
    creator: Field(min_length=1)
    authz: Dict[str, Any]
    created_time: datetime
    updated_time: datetime
    name: Field(min_length=1)
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
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "lists": [
                        {
                            "name": "My Saved List 1",
                            "items": {
                                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
                                    "dataset_guid": "phs000001.v1.p1.c1",
                                },
                                "CF_1": {
                                    "name": "Cohort Filter 1",
                                    "type": "Gen3GraphQL",
                                    "schema_version": "c246d0f",
                                    "data": {
                                        "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter)
    { file_count { histogram { sum } } } } }""",
                                        "variables": {
                                            "filter": {
                                                "AND": [
                                                    {"IN": {"annotated_sex": ["male"]}},
                                                    {
                                                        "IN": {
                                                            "data_type": [
                                                                "Aligned Reads"
                                                            ]
                                                        }
                                                    },
                                                    {"IN": {"data_format": ["CRAM"]}},
                                                    {"IN": {"race": ['["hispanic"]']}},
                                                ]
                                            }
                                        },
                                    },
                                },
                            },
                        },
                    ]
                }
            ]
        }
    }


class IDToItems(BaseModel):
    UUID: Dict[str, Any]


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    version = Column(Integer, nullable=False)
    creator = Column(String, nullable=False, index=True)
    authz = Column(JSONB, nullable=False)

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

    items = Column(JSONB)

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


def is_dict(v: Any):
    assert isinstance(v, dict)
    return v


def is_nonempty(v: Any):
    assert v
    return v
