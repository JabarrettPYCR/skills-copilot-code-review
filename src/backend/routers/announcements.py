"""Public announcements and signed-in teacher management."""

from datetime import date, datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator, model_validator

from ..database import announcements_collection
from .auth import require_teacher

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    expiration_date: date
    start_date: date | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter an announcement message")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.start_date >= self.expiration_date:
            raise ValueError("Start date must be before expiration date")
        return self

    def document(self):
        return {
            "message": self.message,
            "expiration_date": datetime.combine(
                self.expiration_date, datetime.min.time(), timezone.utc
            ),
            "start_date": datetime.combine(
                self.start_date, datetime.min.time(), timezone.utc
            ) if self.start_date else None
        }


def serialize(document):
    return {
        "id": str(document["_id"]),
        "message": document["message"],
        "expiration_date": document["expiration_date"].date().isoformat(),
        "start_date": document["start_date"].date().isoformat() if document.get("start_date") else None
    }


def announcement_id(value):
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=404, detail="Announcement not found")
    return ObjectId(value)


@router.get("")
def list_active():
    """Return announcements started and not yet expired (UTC)."""
    now = datetime.now(timezone.utc)
    documents = announcements_collection.find({
        "$or": [{"start_date": None}, {"start_date": {"$lte": now}}],
        "expiration_date": {"$gt": now}
    }).sort("expiration_date", 1)
    return [serialize(document) for document in documents]


@router.get("/all", dependencies=[Depends(require_teacher)])
def list_all(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return [serialize(document) for document in
            announcements_collection.find().sort("expiration_date", -1)]


@router.post("", status_code=201, dependencies=[Depends(require_teacher)])
def create(announcement: AnnouncementInput):
    document = announcement.document()
    document["_id"] = announcements_collection.insert_one(document).inserted_id
    return serialize(document)


@router.put("/{id}", dependencies=[Depends(require_teacher)])
def update(id: str, announcement: AnnouncementInput):
    document = announcement.document()
    document["_id"] = announcement_id(id)
    result = announcements_collection.update_one(
        {"_id": document["_id"]}, {"$set": announcement.document()}
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return serialize(document)


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_teacher)])
def delete(id: str):
    result = announcements_collection.delete_one({"_id": announcement_id(id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Announcement not found")
