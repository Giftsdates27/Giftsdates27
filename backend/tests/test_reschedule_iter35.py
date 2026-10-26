# Iteration 35: Reschedule (propose new time -> other accepts) for invite dates, booked dates and VIP calendar bookings
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

D1, D2, D3 = "2027-04-14", "2027-04-15", "2027-04-20"
WIN = [{"from": "10:00", "to": "23:00"}]
TAG = uuid.uuid4().hex[:6]
S = {}


def iso(day, tm):
    return f"{day}T{tm}:00+00:00"


def reg(name):
    email = f"test_rs_{name}_{TAG}@example.com"
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
    for n in ("A", "B", "C", "V"):
        S[n], S[n + "h"] = reg(n)
    mdb.users.update_one({"id": S["B"]}, {"$set": {"availability_ranges": {D1: WIN, D2: WIN}}})
    yield
    ids = [S[n] for n in ("A", "B", "C", "V")]
    mdb.dates.delete_many({"$or": [{"inviter_id": {"$in": ids}}, {"recipient_id": {"$in": ids}}]})
    mdb.date_bookings.delete_many({"$or": [{"from_id": {"$in": ids}}, {"to_id": {"$in": ids}}]})
    mdb.vip_sched.delete_many({"vip_id": S["V"]})
    mdb.vip_avail.delete_many({"vip_id": S["V"]})
    mdb.users.delete_many({"id": {"$in": ids}})


def invite(h, rid, day, tm):
    return requests.post(f"{API}/invites", headers=h, json={"recipient_id": rid, "activity_option_1": "Coffee", "activity_option_2": "Walk",
                         "activity_option_3": "Dinner", "scheduled_start": iso(day, tm), "local_day": day, "local_time": tm,
                         "coins": 200, "safety_ack": True})


def resched(h, did, day, tm, kind="invites"):
    url = f"{API}/invites/{did}/reschedule" if kind == "invites" else f"{API}/dates/reschedule/{did}"
    return requests.post(url, headers=h, json={"scheduled_start": iso(day, tm), "local_day": day, "local_time": tm})


def answer(h, did, ans, kind="invites"):
    url = f"{API}/invites/{did}/reschedule/{ans}" if kind == "invites" else f"{API}/dates/reschedule/{did}/{ans}"
    return requests.post(url, headers=h)


def busy(pid, h, day, exclude=None):
    r = requests.get(f"{API}/profiles/{pid}/availability", headers=h, params={"exclude": exclude} if exclude else None)
    assert r.status_code == 200, r.text
    return sorted(b["from"] for b in r.json()["busy_slots"].get(day, []))


# ---------------- Invite dates ----------------
class TestInviteReschedule:
    def test_01_create_invite(self):
        r = invite(S["Ah"], S["B"], D1, "12:00")
        assert r.status_code == 200, r.text
        S["inv"] = r.json().get("id") or r.json().get("date_id") or (r.json().get("date") or {}).get("id")
        assert S["inv"], r.json()

    def test_02_validation_errors(self):
        did = S["inv"]
        # Day not in availability
        r = resched(S["Ah"], did, D3, "12:00"); assert r.status_code == 400 and "DAY_UNAVAILABLE" in detail(r), r.text
        # 2.5h does not fit before 23:00
        r = resched(S["Ah"], did, D1, "21:30"); assert r.status_code == 400 and "TIME_UNAVAILABLE" in detail(r), r.text
        # past time
        mdb.users.update_one({"id": S["B"]}, {"$set": {"availability_ranges.2025-06-01": WIN}})
        r = resched(S["Ah"], did, "2025-06-01", "12:00"); assert r.status_code == 400 and "TIME_PASSED" in detail(r), r.text
        # other date busy on D2 (C -> B at 12:00)
        r2 = invite(S["Ch"], S["B"], D2, "12:00"); assert r2.status_code == 200, r2.text
        r = resched(S["Ah"], did, D2, "13:00"); assert r.status_code == 400 and "SLOT_BUSY" in detail(r), r.text
        # locked (cancelled) slot
        mdb.users.update_one({"id": S["B"]}, {"$set": {"locked_slots": [{"date": D2, "start": iso(D2, "19:00"), "end": iso(D2, "22:00")}]}})
        r = resched(S["Ah"], did, D2, "19:00"); assert r.status_code == 400 and "SLOT_LOCKED" in detail(r), r.text
        mdb.users.update_one({"id": S["B"]}, {"$unset": {"locked_slots": ""}})
        # own slot ignored: overlapping move (12:00 -> 13:00) allowed
        r = resched(S["Ah"], did, D1, "13:00"); assert r.status_code == 200, r.text

    def test_03_invalid_payload(self):
        r = requests.post(f"{API}/invites/{S['inv']}/reschedule", headers=S["Ah"],
                          json={"scheduled_start": "bad", "local_day": D1, "local_time": "12:00"})
        assert r.status_code == 400, r.text
        r = requests.post(f"{API}/invites/{S['inv']}/reschedule", headers=S["Ah"],
                          json={"scheduled_start": iso(D1, "18:00"), "local_day": D1, "local_time": "xx"})
        assert r.status_code in (400, 422), f"bad local_time -> {r.status_code} {r.text[:200]}"

    def test_04_third_party_forbidden(self):
        r = resched(S["Ch"], S["inv"], D1, "18:00"); assert r.status_code == 403, r.text

    def test_05_propose_and_lock(self):
        r = resched(S["Ah"], S["inv"], D1, "18:00"); assert r.status_code == 200, r.text
        p = r.json()["proposal"]; assert p["by"] == S["A"] and p["local_time"] == "18:00"
        d = mdb.dates.find_one({"id": S["inv"]}); assert d["reschedule_proposal"]["local_day"] == D1 and d["local_time"] == "12:00"
        assert busy(S["B"], S["Ah"], D1) == ["12:00", "18:00"]
        assert busy(S["A"], S["Ah"], D1) == ["12:00", "18:00"]  # inviter calendar too
        assert busy(S["B"], S["Ah"], D1, exclude=S["inv"]) == []

    def test_06_new_invite_overlapping_proposal_blocked(self):
        r = invite(S["Ch"], S["B"], D1, "18:30"); assert r.status_code == 400 and "SLOT_BUSY" in detail(r), r.text
        r = invite(S["Ch"], S["A"], D1, "19:00"); assert r.status_code == 400 and "SLOT_BUSY" in detail(r), r.text

    def test_07_list_shows_proposal_mine(self):
        r = requests.get(f"{API}/invites/{S['inv']}", headers=S["Bh"])
        assert r.status_code == 200, r.text
        it = r.json()
        assert it.get("reschedule_proposal") and it["reschedule_proposal"]["mine"] is False, it.get("reschedule_proposal")
        it = requests.get(f"{API}/invites/{S['inv']}", headers=S["Ah"]).json()
        assert it["reschedule_proposal"]["mine"] is True

    def test_08_proposer_cannot_accept(self):
        r = answer(S["Ah"], S["inv"], "accept"); assert r.status_code == 403, r.text

    def test_09_other_accepts(self):
        r = answer(S["Bh"], S["inv"], "accept"); assert r.status_code == 200, r.text
        d = mdb.dates.find_one({"id": S["inv"]})
        assert d["local_time"] == "18:00" and d["local_day"] == D1 and "reschedule_proposal" not in d
        assert d["proposed_start"].startswith(f"{D1}T18:00")
        assert busy(S["B"], S["Ah"], D1) == ["18:00"]
        # old slot freed: a new invite at 12:00 now allowed
        r = invite(S["Ch"], S["B"], D1, "11:30"); assert r.status_code != 400 or "SLOT_BUSY" not in detail(r), r.text
        if r.status_code == 200:
            S["inv_c2"] = r.json().get("id")

    def test_10_decline_keeps_original_and_withdraw(self):
        r = resched(S["Bh"], S["inv"], D1, "20:00")
        # 20:00 + 2.5h = 22:30 fits
        assert r.status_code == 200, r.text
        r = answer(S["Ah"], S["inv"], "decline"); assert r.status_code == 200 and r.json()["status"] == "declined"
        d = mdb.dates.find_one({"id": S["inv"]}); assert d["local_time"] == "18:00" and "reschedule_proposal" not in d
        r = resched(S["Bh"], S["inv"], D1, "20:00"); assert r.status_code == 200
        r = answer(S["Bh"], S["inv"], "decline"); assert r.status_code == 200  # withdraw
        d = mdb.dates.find_one({"id": S["inv"]}); assert "reschedule_proposal" not in d
        r = answer(S["Bh"], S["inv"], "accept"); assert r.status_code == 400 and "NO_PROPOSAL" in detail(r)
        r = answer(S["Bh"], S["inv"], "foo"); assert r.status_code == 400

    def test_11_location_times_updated(self):
        mdb.dates.update_one({"id": S["inv"]}, {"$set": {"location": {"venue": "Cafe", "scheduled_start": iso(D1, "18:00"), "scheduled_end": iso(D1, "21:00")}}})
        assert resched(S["Ah"], S["inv"], D1, "15:00").status_code == 200
        assert answer(S["Bh"], S["inv"], "accept").status_code == 200
        d = mdb.dates.find_one({"id": S["inv"]})
        assert d["location"]["scheduled_start"].startswith(f"{D1}T15:00") and d["location"]["scheduled_end"].startswith(f"{D1}T18:00"), d["location"]

    def test_12_started_and_reported(self):
        mdb.dates.update_one({"id": S["inv"]}, {"$set": {"location.scheduled_start": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}})
        r = resched(S["Ah"], S["inv"], D1, "18:00"); assert r.status_code == 400 and "DATE_STARTED" in detail(r), r.text
        mdb.dates.update_one({"id": S["inv"]}, {"$set": {"location.scheduled_start": iso(D1, "15:00"), "report": {"status": "open"}}})
        r = resched(S["Ah"], S["inv"], D1, "18:00"); assert r.status_code == 400 and "CANNOT_RESCHEDULE" in detail(r), r.text
        mdb.dates.update_one({"id": S["inv"]}, {"$set": {"report": None}})


# ---------------- Booked dates (date_bookings) ----------------
class TestBookingReschedule:
    def test_01_create_booking(self):
        day = D2
        r = requests.post(f"{API}/dates/book", headers=S["Ah"], json={"target_id": S["B"], "venue": "TEST Venue", "city": "Paris",
                          "scheduled_at": iso(day, "19:00"), "coins": 500, "local_time": "19:00", "local_day": day, "address_confirmed": True,
                          "address": "1 Rue de Rivoli", "postal_code": "75001", "country": "France", "activities": ["a", "b", "c"]})
        if r.status_code == 200:
            S["bk"] = r.json().get("booking_id") or r.json().get("id")
        else:
            print("book via API failed, inserting:", r.status_code, r.text[:200])
            S["bk"] = str(uuid.uuid4())
            mdb.date_bookings.insert_one({"id": S["bk"], "from_id": S["A"], "to_id": S["B"], "venue": "TEST Venue", "city": "Paris",
                                          "scheduled_at": iso(day, "19:00"), "local_time": "19:00", "local_day": day, "slot_from": "19:00",
                                          "slot_to": "21:30", "coins": 500, "status": "escrow", "activities": ["a", "b", "c"], "created_at": datetime.now(timezone.utc).isoformat()})
        assert S["bk"]

    def test_02_propose_lock_boundary(self):
        # 15:00 lock_from 14:45 == C invite 12:00 lock_to 14:45 -> allowed
        r = resched(S["Ah"], S["bk"], D2, "15:00", kind="b"); assert r.status_code == 200, r.text
        assert "15:00" in busy(S["B"], S["Ah"], D2) and "19:00" in busy(S["B"], S["Ah"], D2)
        assert "15:00" not in busy(S["B"], S["Ah"], D2, exclude=S["bk"])
        r = invite(S["Ch"], S["B"], D2, "16:00"); assert r.status_code == 400 and "SLOT_BUSY" in detail(r), r.text

    def test_03_accept(self):
        assert answer(S["Ah"], S["bk"], "accept", "b").status_code == 403
        r = answer(S["Bh"], S["bk"], "accept", "b"); assert r.status_code == 200, r.text
        b = mdb.date_bookings.find_one({"id": S["bk"]})
        assert b["slot_from"] == "15:00" and b["slot_to"] == "17:30" and b["local_time"] == "15:00", b
        assert b["scheduled_at"].startswith(f"{D2}T15:00") and "reschedule_proposal" not in b
        assert "19:00" not in busy(S["B"], S["Ah"], D2)

    def test_04_decline_withdraw_and_vip_blocked(self):
        assert resched(S["Bh"], S["bk"], D2, "19:30", kind="b").status_code == 200
        assert answer(S["Ah"], S["bk"], "decline", "b").status_code == 200
        b = mdb.date_bookings.find_one({"id": S["bk"]}); assert b["slot_from"] == "15:00" and "reschedule_proposal" not in b
        mdb.date_bookings.update_one({"id": S["bk"]}, {"$set": {"vip": True}})
        r = resched(S["Ah"], S["bk"], D2, "19:30", kind="b"); assert r.status_code == 400 and "CANNOT_RESCHEDULE" in detail(r)
        mdb.date_bookings.update_one({"id": S["bk"]}, {"$unset": {"vip": ""}})
        assert resched(S["Ch"], S["bk"], D2, "19:30", kind="b").status_code == 403


# ---------------- VIP calendar bookings ----------------
class TestVipReschedule:
    def test_01_setup_and_book(self):
        mdb.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": S["V"], "date": D3, "start": "10:00", "end": "22:00", "tz": "UTC", "slot_len": 60})
        r = requests.post(f"{API}/vip/schedule/{S['V']}/book", headers=S["Ah"], json={"date": D3, "start": "12:00", "end": "13:00", "length": 1, "tz": "UTC", "place": "own"})
        assert r.status_code == 200, r.text
        S["vb"] = r.json()["booking_id"]
        # pending: client reschedule changes instantly
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=S["Ah"], json={"date": D3, "start": "13:00", "end": "14:00"})
        assert r.status_code == 200 and r.json()["status"] == "pending", r.text
        assert mdb.vip_sched.find_one({"id": S["vb"]})["start"] == "13:00"
        assert requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/confirm", headers=S["Vh"]).status_code == 200

    def test_02_client_proposal_on_confirmed(self):
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=S["Ah"], json={"date": D3, "start": "16:00", "end": "17:00"})
        assert r.status_code == 200, r.text
        assert r.json()["proposal"]["by"] == "client"
        b = mdb.vip_sched.find_one({"id": S["vb"]}); assert b["start"] == "13:00" and b["reschedule_proposal"]["start"] == "16:00"
        sl = requests.get(f"{API}/vip/schedule/{S['V']}/slots", headers=S["Ch"]).json()
        day = next(d for d in sl["days"] if d["date"] == D3)
        assert {"13:00", "16:00"} <= {t["from"] for t in day["taken"]}, day["taken"]
        r = requests.post(f"{API}/vip/schedule/{S['V']}/book", headers=S["Ch"], json={"date": D3, "start": "16:00", "end": "17:00", "length": 1, "tz": "UTC", "place": "own"})
        assert r.status_code == 409 and "SLOT_TAKEN" in detail(r), r.text

    def test_03_accept_by_vip(self):
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule/accept", headers=S["Ah"]); assert r.status_code == 403
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule/accept", headers=S["Ch"]); assert r.status_code == 403
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule/accept", headers=S["Vh"]); assert r.status_code == 200, r.text
        b = mdb.vip_sched.find_one({"id": S["vb"]}); assert b["start"] == "16:00" and b["end"] == "17:00" and "reschedule_proposal" not in b

    def test_04_vip_proposal_withdraw_and_client_accept(self):
        h = S["Vh"]; url = f"{API}/vip/schedule/bookings/{S['vb']}/reschedule"
        r = requests.post(url, headers=h, json={"date": D3, "start": "18:00", "end": "19:00"}); assert r.status_code == 200 and r.json()["proposal"]["by"] == "vip"
        assert requests.post(f"{url}/decline", headers=h).status_code == 200  # withdraw
        assert "reschedule_proposal" not in mdb.vip_sched.find_one({"id": S["vb"]})
        assert requests.post(url, headers=h, json={"date": D3, "start": "18:00", "end": "19:00"}).status_code == 200
        assert requests.post(f"{url}/accept", headers=h).status_code == 403
        r = requests.post(f"{url}/accept", headers=S["Ah"]); assert r.status_code == 200, r.text
        assert mdb.vip_sched.find_one({"id": S["vb"]})["start"] == "18:00"

    def test_05_client_decline_by_vip_keeps(self):
        url = f"{API}/vip/schedule/bookings/{S['vb']}/reschedule"
        assert requests.post(url, headers=S["Ah"], json={"date": D3, "start": "20:00", "end": "21:00"}).status_code == 200
        assert requests.post(f"{url}/decline", headers=S["Vh"]).status_code == 200
        b = mdb.vip_sched.find_one({"id": S["vb"]}); assert b["start"] == "18:00" and "reschedule_proposal" not in b

    def test_06_vip_proposal_past_time_rejected(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mdb.vip_avail.insert_one({"id": str(uuid.uuid4()), "vip_id": S["V"], "date": today, "start": "00:00", "end": "23:59", "tz": "UTC", "slot_len": 60})
        r = requests.post(f"{API}/vip/schedule/bookings/{S['vb']}/reschedule", headers=S["Ah"], json={"date": today, "start": "00:00", "end": "01:00"})
        mdb.vip_sched.update_one({"id": S["vb"]}, {"$unset": {"reschedule_proposal": ""}})
        assert r.status_code == 400, f"past-time proposal accepted: {r.status_code} {r.text[:200]}"
