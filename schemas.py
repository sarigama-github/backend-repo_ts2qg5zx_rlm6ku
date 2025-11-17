"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Resource -> "resource" collection
- Roadmap -> "roadmap" collection
- SavedItem -> "saveditem" collection (we will also expose as "saved")
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime


class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar image URL")
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="User preference signals like categories, levels"
    )
    certificates: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    is_active: bool = Field(True, description="Whether user is active")


class Resource(BaseModel):
    """
    Learning resources schema
    Collection name: "resource"
    """
    title: str
    provider: Literal["YouTube", "Course", "PDF", "Repo", "Article", "Other"]
    type: Literal["video", "course", "pdf", "repo", "article", "other"]
    category: str
    level: Literal["Beginner", "Intermediate", "Advanced"]
    link: HttpUrl
    thumbnail: Optional[HttpUrl] = None
    duration: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class Roadmap(BaseModel):
    """
    Roadmaps created by users
    Collection name: "roadmap"
    """
    userId: str = Field(..., description="User id reference")
    title: str
    items: List[Dict[str, Any]] = Field(
        ..., description="Ordered list of resource ids + metadata, e.g., [{'resourceId': 'yt_1', 'done': false}]"
    )
    progress: Optional[float] = Field(0.0, ge=0, le=100)


class SavedItem(BaseModel):
    """
    Saved/Bookmarked items by users
    Collection name: "saveditem"
    """
    userId: str
    resourceId: str
    createdAt: Optional[datetime] = None


# The Flames database viewer may read these via an endpoint.
# Backend endpoints will import these models for validation.
