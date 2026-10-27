# Seed for iteration 38 UI: client (America/Toronto) <-> VIP (Europe/Paris): invite, regular booking, VIP price-list booking, VIP calendar booking
import os, json, uuid, requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PW = "Test@12345"


def day(n): return (datetime.now(timezone.utc) + timedelta(days=n)).strftime("%Y-%m-%d")


def user(key, name, extra):
    email = f"test_i38ui_{key}@example.com"
    old = db.users.find_one({"email": email})
    if old:
        i = old["id"]
        for c, q in (("dates", {"$or": [{"inviter_id": i}, {"recipient_id": i}]}), ("date_bookings", {"$or": [{"from_id": i}, {"to_id": i}]}),
                     ("vip_sched", {"$or": [{"vip_id": i}, {"requester_id": i}]}), ("vip_avail", {"vip_id": i})):
            db[c].delete_many(q)
        db.users.delete_one({"id": i})
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name, "age": 29, "gender": "male",
                                                  "interested_in": "female", "city": "Paris", "country": "France"}).json()
    s = {"coins": 50000, "email_verified": True, "onboarded": True, **extra}
    db.users.update_one({"id": r["user"]["id"]}, {"$set": s})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}, r["token"]


vu = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
C, Ch, Ct = user("c", "Tom", {"timezone": "America/Toronto"})
V, Vh, Vt = user("v", "Vera", {"timezone": "Europe/Paris", "vip_until": vu, "vip": {"prices": {"hour": 300, "h2": 500, "h3": 700, "extra": 250}}})
out = {"C": C, "V": V, "Ct": Ct, "Vt": Vt}
# invite C -> V at day 5 18:00Z (= 14:00 Toronto, 19:00 Paris in winter / depends on DST)
st = datetime.fromisoformat(f"{day(5)}T18:00:00+00:00")
r = requests.post(f"{API}/invites", headers=Ch, json={"recipient_id": V, "activity_option_1": "Coffee", "activity_option_2": "Walk", "activity_option_3": "Dinner",
                  "scheduled_start": st.isoformat(), "local_day": day(5), "local_time": "18:00", "coins": 300, "safety_ack": True})
out["invite"] = r.json().get("id") if r.status_code == 200 else r.text
# regular booked date C -> V day 6 17:00Z
r = requests.post(f"{API}/dates/book", headers=Ch, json={"target_id": V, "venue": "TEST Cafe", "city": "Paris", "scheduled_at": f"{day(6)}T17:00:00+00:00",
                  "local_day": day(6), "local_time": "17:00", "coins": 300, "address_confirmed": True, "address": "1 Rue", "postal_code": "75001",
                  "country": "France", "activities": ["Coffee", "Walk", "Dinner"]})
out["booking"] = r.json().get("booking_id") if r.status_code == 200 else r.text
# VIP price-list booking C -> V day 3 12:00 Paris wall clock, 2h
r = requests.post(f"{API}/vip/book", headers=Ch, json={"target_id": V, "venue": "VIP", "place": "own", "city": "Paris", "scheduled_at": f"{day(3)}T12:00:00", "coins": 1, "vip_length": 2})
out["vipbook"] = r.json().get("booking_id") if r.status_code == 200 else r.text
r = requests.post(f"{API}/vip/book", headers=Ch, json={"target_id": V, "venue": "VIP", "place": "own", "city": "Paris", "scheduled_at": f"{day(4)}T15:00:00", "coins": 1, "vip_length": 1})
out["vipbook2"] = r.json().get("booking_id") if r.status_code == 200 else r.text
# VIP calendar booking (vip_sched) in Paris tz
db.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": V, "date": day(7), "start": "10:00", "end": "16:00", "tz": "Europe/Paris", "slot_len": 60})
r = requests.post(f"{API}/vip/schedule/{V}/book", headers=Ch, json={"date": day(7), "start": "12:00", "end": "13:00", "length": 1, "tz": "Europe/Paris", "place": "other", "address": "1 Rue de Rivoli",
                  "city": "Paris", "postal_code": "75001", "country": "France", "address_confirmed": True})
out["vsched"] = r.json().get("booking_id") if r.status_code == 200 else r.text
out["days"] = {n: day(n) for n in (3, 4, 5, 6, 7)}
print(json.dumps(out, indent=1))
