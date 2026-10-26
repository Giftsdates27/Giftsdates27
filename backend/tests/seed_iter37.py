# Seed for iteration 37: VIP suggestions / client counter-offer + regular decline quick times
import os, json, uuid, requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PW = "Test@12345"


def day(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).strftime("%Y-%m-%d")


def user(key, name, vip=False, extra=None):
    email = f"test_i37_{key}@example.com"
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
    if vip: s["vip_until"] = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    if extra: s.update(extra)
    db.users.update_one({"id": r["user"]["id"]}, {"$set": s})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}, email


def vbook(h, vid, n, st):
    r = requests.post(f"{API}/vip/schedule/{vid}/book", headers=h, json={"date": day(n), "start": st, "end": f"{int(st[:2])+1:02d}:00",
                                                                     "length": 1, "tz": "UTC", "place": "other", "address": "1 Rue de Rivoli",
                                                                     "city": "Paris", "postal_code": "75001", "country": "France", "address_confirmed": True})
    assert r.status_code == 200, r.text
    return r.json()["booking_id"]


def seed():
    out = {}
    A, Ah, Ae = user("a", "TEST Client")
    V, Vh, Ve = user("v", "TEST Vip", vip=True)
    for n in (3, 4):
        db.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": V, "date": day(n), "start": "10:00", "end": "16:00", "tz": "UTC", "slot_len": 60})
    out["pending"] = vbook(Ah, V, 3, "12:00")
    out["confirmed"] = vbook(Ah, V, 4, "12:00")
    requests.post(f"{API}/vip/schedule/bookings/{out['confirmed']}/confirm", headers=Vh)
    out["pending2"] = vbook(Ah, V, 3, "14:00")  # VIP proposes on this pending one
    out["confirmed2"] = vbook(Ah, V, 4, "14:00")
    requests.post(f"{API}/vip/schedule/bookings/{out['confirmed2']}/confirm", headers=Vh)
    # VIP proposes new times on confirmed2 and pending2
    r = requests.post(f"{API}/vip/schedule/bookings/{out['confirmed2']}/reschedule", headers=Vh, json={"date": day(4), "start": "10:00", "end": "11:00"})
    assert r.status_code == 200, r.text
    r = requests.post(f"{API}/vip/schedule/bookings/{out['pending2']}/reschedule", headers=Vh, json={"date": day(3), "start": "10:00", "end": "11:00"})
    assert r.status_code == 200, r.text

    # regular: recipient R with availability 18:00-23:00 on days 2..6, inviter I
    ranges = {day(n): [{"from": "18:00", "to": "23:00"}] for n in range(2, 7)}
    R, Rh, Re = user("r", "TEST Recipient", extra={"availability_ranges": ranges})
    I, Ih, Ie = user("i", "TEST Inviter")
    # invite at day2 19:00 local, local clock is UTC-5 (scheduled_start 00:00Z next day)
    st = datetime.fromisoformat(f"{day(2)}T19:00:00-05:00")
    r = requests.post(f"{API}/invites", headers=Ih, json={"recipient_id": R, "activity_option_1": "Coffee", "activity_option_2": "Walk", "activity_option_3": "Dinner",
                                                        "scheduled_start": st.isoformat(), "local_day": day(2), "local_time": "19:00", "coins": 300, "safety_ack": True})
    assert r.status_code == 200, r.text
    out["invite"] = r.json()["id"]
    # booked date (escrow) I -> R at day3 19:00 local (UTC)
    r = requests.post(f"{API}/dates/book", headers=Ih, json={"target_id": R, "venue": "TEST Cafe", "city": "Paris", "scheduled_at": f"{day(3)}T19:00:00+00:00",
                                                           "local_day": day(3), "local_time": "19:00", "coins": 300, "address_confirmed": True,
                                                           "address": "1 Rue", "postal_code": "75001", "country": "France", "activities": ["Coffee", "Walk", "Dinner"]})
    assert r.status_code == 200, r.text
    out["booking"] = r.json()["booking_id"]
    out.update({"A": [Ae, PW, A], "V": [Ve, PW, V], "R": [Re, PW, R], "I": [Ie, PW, I]})
    return out


if __name__ == "__main__":
    print(json.dumps(seed()))
