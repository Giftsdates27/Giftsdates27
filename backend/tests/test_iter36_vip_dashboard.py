# Iteration 36: verify iter35 fixes (names in /api/dates, VIP TIME_PASSED/DATE_STARTED, slots?exclude) + VIP dashboard data buckets
import os
import uuid
import requests
import pytest
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
TAG = uuid.uuid4().hex[:6]
S = {}
D = "2027-05-12"


def reg(name):
    email = f"test_i36_{name}_{TAG}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "Test@12345", "name": f"TEST_{name}", "age": 28,
                                                  "gender": "male", "interested_in": "female", "city": "Paris", "country": "France"})
    assert r.status_code == 200, r.text
    j = r.json()
    mdb.users.update_one({"id": j["user"]["id"]}, {"$set": {"coins": 20000, "email_verified": True}})
    return j["user"]["id"], {"Authorization": f"Bearer {j['token']}"}


def detail(r):
    try:
        return str(r.json().get("detail"))
    except Exception:
        return r.text


@pytest.fixture(scope="module", autouse=True)
def setup():
    for n in ("A", "B", "V"):
        S[n], S[n + "h"] = reg(n)
    mdb.users.update_one({"id": S["B"]}, {"$set": {"availability_ranges": {D: [{"from": "10:00", "to": "23:00"}]}}})
    mdb.users.update_one({"id": S["V"]}, {"$set": {"vip_until": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()}})
    mdb.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": S["V"], "date": D, "start": "10:00", "end": "22:00", "tz": "UTC", "slot_len": 60})
    yield
    ids = [S[n] for n in ("A", "B", "V")]
    mdb.dates.delete_many({"$or": [{"inviter_id": {"$in": ids}}, {"recipient_id": {"$in": ids}}]})
    mdb.date_bookings.delete_many({"$or": [{"from_id": {"$in": ids}}, {"to_id": {"$in": ids}}]})
    mdb.vip_sched.delete_many({"vip_id": S["V"]})
    mdb.vip_avail.delete_many({"vip_id": S["V"]})
    mdb.users.delete_many({"id": {"$in": ids}})


def book_vip(h, start, end):
    r = requests.post(f"{API}/vip/schedule/{S['V']}/book", headers=h, json={"date": D, "start": start, "end": end, "length": 1, "tz": "UTC", "place": "own"})
    assert r.status_code == 200, r.text
    return r.json()["booking_id"]


# ---- /api/dates names fix ----
class TestDatesNames:
    def test_from_to_names(self):
        r = requests.post(f"{API}/dates/book", headers=S["Ah"], json={"target_id": S["B"], "venue": "TEST Venue", "city": "Paris",
                          "scheduled_at": f"{D}T19:00:00+00:00", "coins": 500, "local_time": "19:00", "local_day": D, "address_confirmed": True,
                          "address": "1 Rue de Rivoli", "postal_code": "75001", "country": "France", "activities": ["a", "b", "c"]})
        assert r.status_code == 200, r.text
        bid = r.json().get("booking_id") or r.json().get("id")
        out = requests.get(f"{API}/dates", headers=S["Ah"]).json()["outgoing"]
        row = next(b for b in out if b["id"] == bid)
        assert row.get("to_name") == "TEST_B", row.get("to_name")
        inc = requests.get(f"{API}/dates", headers=S["Bh"]).json()["incoming"]
        row = next(b for b in inc if b["id"] == bid)
        assert row.get("from_name") == "TEST_A", row.get("from_name")


# ---- VIP reschedule validation fixes ----
class TestVipRescheduleFixes:
    def test_01_slots_exclude(self):
        S["vb"] = book_vip(S["Ah"], "12:00", "13:00")
        sl = requests.get(f"{API}/vip/schedule/{S['V']}/slots", headers=S["Ah"]).json()
        day = next(d for d in sl["days"] if d["date"] == D)
        assert "12:00" in {t["from"] for t in day["taken"]}
        sl = requests.get(f"{API}/vip/schedule/{S['V']}/slots", headers=S["Ah"], params={"exclude": S["vb"]}).json()
        day = next(d for d in sl["days"] if d["date"] == D)
        assert "12:00" not in {t["from"] for t in day["taken"]}, day["taken"]
        # adjacent slot (13:00) should be offered as free when own booking excluded
        free = [s for s in day["slots"] if s.get("start", s.get("from")) in ("12:00", "13:00")]
        print("slots near own booking (excluded):", free)

    def test_02_pending_reschedule_adjacent_time(self):
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=S["Ah"], json={"date": D, "start": "12:30", "end": "13:30"})
        assert r.status_code == 200, r.text
        assert mdb.vip_sched.find_one({"id": S["vb"]})["start"] == "12:30"

    def test_03_time_passed_both_sides(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mdb.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": S["V"], "date": today, "start": "00:00", "end": "23:59", "tz": "UTC", "slot_len": 60})
        for h in (S["Ah"], S["Vh"]):
            r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=h, json={"date": today, "start": "00:00", "end": "01:00"})
            assert r.status_code == 400 and "TIME_PASSED" in detail(r), r.text
        assert "reschedule_proposal" not in mdb.vip_sched.find_one({"id": S["vb"]})

    def test_04_date_started_rejected(self):
        assert requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/confirm", headers=S["Vh"]).status_code == 200
        orig = mdb.vip_sched.find_one({"id": S["vb"]}, {"_id": 0, "date": 1, "start": 1})
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d")
        mdb.vip_sched.update_one({"id": S["vb"]}, {"$set": {"date": past, "start": (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%H:%M")}})
        try:
            for h in (S["Ah"], S["Vh"]):
                r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=h, json={"date": D, "start": "15:00", "end": "16:00"})
                assert r.status_code == 400 and "DATE_STARTED" in detail(r), r.text
        finally:
            mdb.vip_sched.update_one({"id": S["vb"]}, {"$set": orig})

    def test_05_accept_rejects_if_started(self):
        url = f"{API}/vip/schedule/bookings/{S['vb']}/reschedule"
        assert requests.post(url, headers=S["Ah"], json={"date": D, "start": "16:00", "end": "17:00"}).status_code == 200
        orig = mdb.vip_sched.find_one({"id": S["vb"]}, {"_id": 0, "date": 1, "start": 1})
        mdb.vip_sched.update_one({"id": S["vb"]}, {"$set": {"date": (datetime.now(timezone.utc)).strftime("%Y-%m-%d"),
                                                             "start": (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%H:%M")}})
        try:
            r = requests.post(f"{url}/accept", headers=S["Vh"])
            assert r.status_code == 400 and "DATE_STARTED" in detail(r), r.text
        finally:
            mdb.vip_sched.update_one({"id": S["vb"]}, {"$set": orig, "$unset": {"reschedule_proposal": ""}})


# ---- VIP dashboard data sources ----
class TestVipDashboardData:
    def test_buckets(self):
        b_pend = book_vip(S["Bh"], "18:00", "19:00")
        b_decl = book_vip(S["Bh"], "20:00", "21:00")
        assert requests.post(f"{API}/vip/schedule/bookings/{b_decl}/decline", headers=S["Vh"], params={"reason": "TEST"}).status_code == 200
        me = requests.get(f"{API}/vip/schedule/me", headers=S["Vh"]).json()
        assert me["is_vip"] is True
        assert b_pend in [x["id"] for x in me["pending"]]
        assert S["vb"] in [x["id"] for x in me["confirmed"]]
        assert b_decl in [x["id"] for x in me["past"]]
        assert all("_id" not in x for x in me["pending"] + me["confirmed"] + me["past"])
        mine = requests.get(f"{API}/vip/schedule/bookings/mine", headers=S["Bh"]).json()["requests"]
        st = {x["id"]: x["status"] for x in mine}
        assert st[b_pend] == "pending" and st[b_decl] == "declined"
        assert all(x["vip_card"]["name"] == "TEST_V" for x in mine)
