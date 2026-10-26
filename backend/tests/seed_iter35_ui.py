# Seed for iteration 35 UI test: reschedule on /dates (invite + booking) and /vip-bookings (confirmed VIP booking)
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

def user(key, name):
    email = f"test_rs35_{key}@example.com"
    old = db.users.find_one({"email": email})
    if old:
        ids = old["id"]
        db.dates.delete_many({"$or": [{"inviter_id": ids}, {"recipient_id": ids}]})
        db.date_bookings.delete_many({"$or": [{"from_id": ids}, {"to_id": ids}]})
        db.vip_sched.delete_many({"$or": [{"vip_id": ids}, {"requester_id": ids}]})
        db.vip_avail.delete_many({"vip_id": ids})
        db.users.delete_one({"id": ids})
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name, "age": 29, "gender": "male",
                                                  "interested_in": "female", "city": "Paris", "country": "France"}).json()
    db.users.update_one({"id": r["user"]["id"]}, {"$set": {"coins": 20000, "email_verified": True, "onboarded": True}})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}, email

A, Ah, Ae = user("a", "TEST Alice")
B, Bh, Be = user("b", "TEST Bob")
V, Vh, Ve = user("v", "TEST Vip")
db.users.update_one({"id": B}, {"$set": {"availability_weekly": {str(i): [{"from": "10:00", "to": "23:00"}] for i in range(7)}}})
db.users.update_one({"id": V}, {"$set": {"vip_until": (now + timedelta(days=60)).isoformat()}})

r = requests.post(f"{API}/invites", headers=Ah, json={"recipient_id": B, "activity_option_1": "Coffee", "activity_option_2": "Walk",
                  "activity_option_3": "Dinner", "scheduled_start": f"{day(3)}T12:00:00+00:00", "local_day": day(3), "local_time": "12:00", "coins": 200, "safety_ack": True})
out["invite"] = r.json().get("id"); print("invite", r.status_code, r.text[:120])
r = requests.post(f"{API}/dates/book", headers=Ah, json={"target_id": B, "venue": "TEST Venue", "city": "Paris", "scheduled_at": f"{day(4)}T19:00:00+00:00",
                  "coins": 500, "local_time": "19:00", "local_day": day(4), "address_confirmed": True, "address": "1 Rue de Rivoli", "postal_code": "75001", "country": "France", "activities": ["a", "b", "c"]})
out["booking"] = r.json().get("booking_id") or r.json().get("id"); print("booking", r.status_code, r.text[:120])
db.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": V, "date": day(5), "start": "10:00", "end": "22:00", "tz": "UTC", "slot_len": 60})
r = requests.post(f"{API}/vip/schedule/{V}/book", headers=Ah, json={"date": day(5), "start": "12:00", "end": "13:00", "length": 1, "tz": "UTC", "place": "own"})
out["vip_booking"] = r.json().get("booking_id"); print("vip", r.status_code, r.text[:120])
print(requests.post(f"{API}/vip/schedule/bookings/{out['vip_booking']}/confirm", headers=Vh).status_code)
out.update({"A": [Ae, PW, A], "B": [Be, PW, B], "V": [Ve, PW, V], "days": [day(3), day(4), day(5)]})
print(json.dumps(out))
