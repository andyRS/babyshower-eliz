from datetime import datetime, timezone
from uuid import uuid4
import hmac

from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_db: str = "babyshower_eliz"
    admin_password: str
    secret_key: str
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
gifts = client[settings.mongodb_db]["gifts"]
meta = client[settings.mongodb_db]["meta"]
signer = URLSafeTimedSerializer(settings.secret_key)
app = FastAPI(title="Eliz Maribeth Baby Shower API")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

@app.on_event("startup")
def seed_example_gifts():
    if gifts.estimated_document_count() == 0:
        try:
            meta.insert_one({"_id": "initial_gifts", "created_at": datetime.now(timezone.utc)})
        except DuplicateKeyError:
            return
        examples = [
            ("Pampers #2", "Pañales y cuidado", "Pañales talla 2.", 1, "baby"),
            ("Pampers #3", "Pañales y cuidado", "Pañales talla 3.", 1, "baby"),
            ("Pampers #4", "Pañales y cuidado", "Pañales talla 4.", 1, "baby"),
            ("Pampers #5", "Pañales y cuidado", "Pañales talla 5.", 1, "baby"),
            ("Wipes", "Pañales y cuidado", "Toallitas húmedas para bebé.", 1, "sparkles"),
            ("Baberos de hombro", "Ropita y textiles", "Para acompañar sus comidas.", 1, "shirt"),
            ("Mantas", "Ropita y textiles", "Para arropar a Eliz.", 1, "heart"),
            ("Juego de gimnasio", "Juegos y descanso", "Para sus primeros juegos.", 1, "sparkles"),
            ("Corral", "Juegos y descanso", "Un espacio cómodo y seguro.", 1, "baby"),
            ("Gavetero de bebé", "Habitación", "Para organizar sus cositas.", 1, "gift"),
            ("Bañito", "Baño y cuidado", "Bañera para bebé.", 1, "bath"),
            ("Biberones pequeños", "Alimentación", "Biberones de tamaño pequeño.", 1, "milk"),
            ("Biberones grandes", "Alimentación", "Biberones de tamaño grande.", 1, "milk"),
            ("Gel de baño de bebé", "Baño y cuidado", "Gel suave para sus baños.", 1, "bath"),
            ("Crema de bebé", "Baño y cuidado", "Crema para cuidar su piel.", 1, "heart"),
            ("Toalla para bebé", "Baño y cuidado", "Una toalla suave para Eliz.", 1, "bath"),
        ]
        gifts.insert_many([{"_id": str(uuid4()), "title": title, "category": category, "description": description, "quantity": quantity, "icon": icon, "reservations": [], "created_at": datetime.now(timezone.utc)} for title, category, description, quantity, icon in examples])


class ReservationIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class GiftIn(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    category: str = Field(default="Esenciales", max_length=40)
    description: str = Field(default="", max_length=240)
    quantity: int = Field(ge=1, le=1000)
    icon: str = Field(default="gift", max_length=30)


class LoginIn(BaseModel):
    password: str


def require_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Acceso de administrador requerido")
    try:
        if signer.loads(authorization[7:], max_age=86400) != "admin":
            raise BadSignature("Invalid role")
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Sesión vencida o inválida")


def public_gift(gift):
    reservations = gift.get("reservations", [])
    return {"id": gift["_id"], "title": gift["title"], "category": gift["category"], "description": gift.get("description", ""), "quantity": gift["quantity"], "reserved": len(reservations), "available": max(0, gift["quantity"] - len(reservations)), "icon": gift.get("icon", "gift")}


@app.get("/api/health")
def health():
    client.admin.command("ping")
    return {"ok": True}


@app.get("/api/gifts")
def list_gifts():
    return [public_gift(g) for g in gifts.find().sort("created_at", 1)]


@app.post("/api/gifts/{gift_id}/reserve")
def reserve(gift_id: str, data: ReservationIn):
    name = " ".join(data.name.strip().split())
    if len(name) < 2:
        raise HTTPException(422, "Escribe tu nombre")
    reservation = {"id": str(uuid4()), "name": name, "created_at": datetime.now(timezone.utc)}
    gift = gifts.find_one_and_update(
        {"_id": gift_id, "$expr": {"$lt": [{"$size": {"$ifNull": ["$reservations", []]}}, "$quantity"]}},
        {"$push": {"reservations": reservation}}, return_document=ReturnDocument.AFTER,
    )
    if gift is None:
        if gifts.find_one({"_id": gift_id}) is None:
            raise HTTPException(404, "Regalo no encontrado")
        raise HTTPException(409, "Este regalo ya está completo")
    return {"reservation_id": reservation["id"], "gift": public_gift(gift)}


@app.post("/api/admin/login")
def login(data: LoginIn):
    if not hmac.compare_digest(data.password, settings.admin_password):
        raise HTTPException(401, "Contraseña incorrecta")
    return {"token": signer.dumps("admin")}


@app.get("/api/admin/gifts", dependencies=[Depends(require_admin)])
def admin_gifts():
    return [{**public_gift(g), "reservations": [{"id": r["id"], "name": r["name"], "created_at": r["created_at"].isoformat()} for r in g.get("reservations", [])]} for g in gifts.find().sort("created_at", 1)]


@app.post("/api/admin/gifts", dependencies=[Depends(require_admin)])
def create_gift(data: GiftIn):
    gift = {"_id": str(uuid4()), **data.model_dump(), "reservations": [], "created_at": datetime.now(timezone.utc)}
    gifts.insert_one(gift)
    return public_gift(gift)


@app.patch("/api/admin/gifts/{gift_id}", dependencies=[Depends(require_admin)])
def update_gift(gift_id: str, data: GiftIn):
    gift = gifts.find_one({"_id": gift_id})
    if not gift:
        raise HTTPException(404, "Regalo no encontrado")
    if data.quantity < len(gift.get("reservations", [])):
        raise HTTPException(409, "La cantidad no puede ser menor que las reservas actuales")
    updated = gifts.find_one_and_update({"_id": gift_id, "$expr": {"$lte": [{"$size": {"$ifNull": ["$reservations", []]}}, data.quantity]}}, {"$set": data.model_dump()}, return_document=ReturnDocument.AFTER)
    if updated is None:
        raise HTTPException(409, "Entró una nueva reserva; aumenta la cantidad y vuelve a intentar")
    return public_gift(updated)


@app.delete("/api/admin/gifts/{gift_id}/reservations/{reservation_id}", dependencies=[Depends(require_admin)])
def remove_reservation(gift_id: str, reservation_id: str):
    result = gifts.update_one({"_id": gift_id, "reservations.id": reservation_id}, {"$pull": {"reservations": {"id": reservation_id}}})
    if not result.modified_count:
        raise HTTPException(404, "Reserva no encontrada")
    return {"ok": True}


@app.delete("/api/admin/gifts/{gift_id}", dependencies=[Depends(require_admin)])
def delete_gift(gift_id: str):
    gift = gifts.find_one({"_id": gift_id})
    if not gift:
        raise HTTPException(404, "Regalo no encontrado")
    if gift.get("reservations"):
        raise HTTPException(409, "Quita las reservas antes de eliminar el regalo")
    gifts.delete_one({"_id": gift_id})
    return {"ok": True}
