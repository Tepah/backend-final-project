from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Permission(BaseModel):
    _id: str
    name: str = Field(None, title="Type of permission", max_length=20)
    desc: str = Field(None, title="Description of Permission")
    access: str = Field(None, title="Access point")


class Subscription(BaseModel):
    _id: str
    name: str = Field(None, title="Type of Subscription")
    desc: str = Field(None, title="Description of Subscription")
    permissions: List[str] = Field(default=[], title="All Permission IDs")
    requests: int = Field(0, title="Amount of Requests made")
    access_limit: int = Field(None, title="How many times a user can request")
    start_date: datetime = Field(None, title="When Subscription was made")
    auto: bool = Field(False, title="Automatically renew")


class Customer(BaseModel):
    _id: str
    admin: bool = Field(False, title="Admin status")
    username: str = Field(None, title="The description of the item", max_length=10)
    password: str = Field(None, title="Password to login", max_length=10)
    subscription: str = Field(None)
