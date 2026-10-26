# Seed for iteration 36 UI test: VIP dashboard (/vip-bookings) with every bucket populated
import os, json, uuid, requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PW = "Test@12345"
now = datetime.now(timezone.utc)
day = lambda n: (now + timedelta(days=n)).strftime("%Y-%m-%d")
out = {}


def user(key, name, vip=False):
    email = f"test_i36_{key}@example.com"
    old = db.users.find_one({"email": email})
    if old:
        i = old["id"]
        db.dates.delete_many({"$or": [{"inviter_id": i}, {"recipient_id": i}]})
        db.date_bookings.delete_many({"$or": [{"from_id": i}, {"to_id": i}]})
        db.vip_sched.delete_many({"$or": [{"vip_id": i}, {"requester_id": i}]})
        db.vip_avail.delete_many({"vip_id": i})
        db.users.delete_one({"id": i})
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name, "age": 29, "gender": "male",
                                                  "interested_in": "female", "city": "Paris", "country": "France"}).json()
    s = {"coins": 50000, "email_verified": True, "onboarded": True}
    if vip: s["vip_until"] = (now + timedelta(days=60)).isoformat()
    db.users.update_one({"id": r["user"]["id"]}, {"$set": s})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}, email


A, Ah, Ae = user("a", "TEST Alice")
V, Vh, Ve = user("v", "TEST Vip", vip=True)
W, Wh, We = user("w", "TEST Wvip", vip=True)
for vid in (V, W):
    for n in (3, 4, 5):
        db.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": vid, "date": day(n), "start": "10:00", "end": "22:00", "tz": "UTC", "slot_len": 60})


def book(h, vid, n, st):
    r = requests.post(f"{API}/vip/schedule/{vid}/book", headers=h, json={"date": day(n), "start": st, "end": f"{int(st[:2])+1:02d}:00", "length": 1, "tz": "UTC", "place": "other", "address": "1 Rue de Rivoli", "city": "Paris", "postal_code": "75001", "country": "France", "address_confirmed": True})
    assert r.status_code == 200, r.text
    return r.json()["booking_id"]


# incoming to V (from A)
out["pending"] = book(Ah, V, 3, "12:00")
out["confirmed"] = book(Ah, V, 4, "12:00"); requests.post(f"{API}/vip/schedule/bookings/{out['confirmed']}/confirm", headers=Vh)
out["declined"] = book(Ah, V, 5, "12:00"); requests.post(f"{API}/vip/schedule/bookings/{out['declined']}/decline", headers=Vh, params={"reason": "TEST busy"})
out["cancelled"] = book(Ah, V, 5, "15:00"); requests.post(f"{API}/vip/schedule/bookings/{out['cancelled']}/cancel", headers=Ah)
out["reported"] = book(Ah, V, 3, "16:00"); db.vip_sched.update_one({"id": out["reported"]}, {"$set": {"status": "reported", "report": {"status": "open", "reasons": ["no_show"], "created_at": now.isoformat()}}})
out["completed"] = book(Ah, V, 4, "18:00"); db.vip_sched.update_one({"id": out["completed"]}, {"$set": {"status": "completed", "date": day(-2), "completed_at": now.isoformat()}})
# outgoing from V (V books W)
out["v_mine"] = book(Vh, W, 3, "12:00")
# VIP price-list booking (date_bookings vip=true) A -> V
r = requests.post(f"{API}/vip/book", headers=Ah, json={"target_id": V, "venue": "TEST VIP Venue", "city": "Paris", "scheduled_at": f"{day(6)}T19:00:00+00:00",
                  "coins": 300, "place": "your", "address": "1 Rue de Rivoli", "postal_code": "75001", "country": "France", "address_confirmed": True, "activities": ["a", "b", "c"]})
print("vip/book", r.status_code, r.text[:200])
out["pricelist"] = r.json().get("booking_id") or r.json().get("id")
out.update({"A": [Ae, PW, A], "V": [Ve, PW, V], "W": [We, PW, W]})
print(json.dumps(out))
for k in ("pending", "confirmed", "declined", "cancelled", "reported", "completed", "v_mine"):
    print(k, db.vip_sched.find_one({"id": out[k]}, {"_id": 0, "status": 1})["status"])
