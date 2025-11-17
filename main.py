import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Resource, Roadmap, SavedItem, User

app = FastAPI(title="Smart Study Recommender API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -----------------------------
# API: Recommendations & Search
# -----------------------------

class RecommendationsResponse(BaseModel):
    data: List[Dict[str, Any]]
    meta: Dict[str, Any]


def _resource_to_public(doc: Dict[str, Any]) -> Dict[str, Any]:
    # Mongo returns _id; convert to string id
    if doc is None:
        return {}
    d = {k: v for k, v in doc.items() if k != "_id"}
    if "_id" in doc:
        d["id"] = str(doc["_id"]) if not isinstance(doc["_id"], str) else doc["_id"]
    return d


@app.get("/api/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    category: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    userId: Optional[str] = Query(None),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filt: Dict[str, Any] = {}
    if category:
        filt["category"] = {"$regex": f"^{category}$", "$options": "i"}
    if level:
        filt["level"] = {"$regex": f"^{level}$", "$options": "i"}

    # Sort by popularity or created_at desc if available
    cursor = db["resource"].find(filt).sort([("metadata.views", -1), ("created_at", -1)])
    total = cursor.count() if hasattr(cursor, 'count') else db["resource"].count_documents(filt)

    skip = (page - 1) * limit
    items = cursor.skip(skip).limit(limit)
    data = [_resource_to_public(x) for x in items]

    return {
        "data": data,
        "meta": {"page": page, "limit": limit, "total": total}
    }


@app.get("/api/resource/{res_id}")
def get_resource(res_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["resource"].find_one({"_id": res_id}) or db["resource"].find_one({"id": res_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _resource_to_public(doc)


# -----------------------------
# API: Roadmaps & Saved items
# -----------------------------

@app.post("/api/roadmap")
def create_roadmap(payload: Roadmap):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    inserted_id = create_document("roadmap", payload)
    return {"ok": True, "id": inserted_id}


@app.patch("/api/roadmap/{roadmap_id}")
def update_roadmap(roadmap_id: str, body: Dict[str, Any]):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    res = db["roadmap"].update_one({"_id": roadmap_id}, {"$set": body})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"ok": True}


@app.post("/api/saved")
def save_item(payload: SavedItem):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    data = payload.model_dump()
    # Upsert to avoid duplicates per user/resource
    db["saveditem"].update_one(
        {"userId": data["userId"], "resourceId": data["resourceId"]},
        {"$setOnInsert": data},
        upsert=True,
    )
    return {"ok": True}


@app.get("/api/search")
def search(q: str, category: Optional[str] = None, level: Optional[str] = None, limit: int = 20):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filt: Dict[str, Any] = {
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}},
        ]
    }
    if category:
        filt["category"] = {"$regex": category, "$options": "i"}
    if level:
        filt["level"] = {"$regex": level, "$options": "i"}

    cursor = db["resource"].find(filt).limit(min(50, max(1, limit)))
    return {"data": [_resource_to_public(x) for x in cursor]}


# -----------------------------
# API: Schema exposure (for viewers/tools)
# -----------------------------

@app.get("/schema")
def get_schema_definitions():
    return {
        "models": [
            "User",
            "Resource",
            "Roadmap",
            "SavedItem",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
