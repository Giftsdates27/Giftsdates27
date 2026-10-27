# Iteration 39: VIP calendar bookings (vip_sched) lock the NORMAL calendar of VIP + client (±15 min) and vice versa
import os, uuid, requests, pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PW = "Test@12345"
TOR = ZoneInfo("America/Toronto")


def day(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).strftime("%Y-%m-%d")


D, D2, D3 = day(10), day(12), day(11)


def iso_local(d, hm, tz=TOR):
    return datetime.fromisoformat(f"{d}T{hm}:00").replace(tzinfo=tz).isoformat()


def mk(key, name, extra=None):
    email = f"test_i39_{key}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name, "age": 29, "gender": "male",
                                                  "interested_in": "female", "city": "Toronto", "country": "Canada"})
    assert r.status_code == 200, r.text
    r = r.json()
    s = {"coins": 50000, "email_verified": True, "onboarded": True, "timezone": "America/Toronto"}
    if extra: s.update(extra)
    db.users.update_one({"id": r["user"]["id"]}, {"$set": s})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}


def vs_doc(vip, req, date, start, end, status="confirmed", tz="America/Toronto", prop=None):
    sm = int(start[:2]) * 60 + int(start[3:]); em = int(end[:2]) * 60 + int(end[3:])
    f = lambda m: f"{(m // 60) % 24:02d}:{m % 60:02d}"
    d = {"id": f"TEST_i39_{uuid.uuid4().hex[:8]}", "vip_id": vip, "requester_id": req, "date": date, "start": start, "end": end,
         "lock_start": f(max(0, sm - 15)), "lock_end": f(em + 15), "status": status, "tz": tz, "coins": 300,
         "hours": (em - sm) // 60, "length": (em - sm) // 60, "place": "own", "location": {}, "created_at": datetime.now(timezone.utc).isoformat()}
    if prop: d["reschedule_proposal"] = prop
    db.vip_sched.insert_one(d)
    return d["id"]


@pytest.fixture(scope="module")
def ppl():
    vip_until = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    V, Vh = mk("v", "TEST Vip39", {"vip_until": vip_until, "vip": {"prices": {"hour": 300, "h2": 500, "h3": 700, "extra": 250}, "places": ["own"]}, "vip_own_place": {"address": "1 Test St"}})
    C, Ch = mk("c", "TEST Client39")
    X, Xh = mk("x", "TEST Other39")
    ids = {
        "vs1": vs_doc(V, C, D, "19:00", "21:00"),
        "vs2": vs_doc(V, C, D, "12:00", "13:00", status="pending", prop={"date": D, "start": "15:00", "end": "16:00", "by": "vip", "at": "x"}),
        "vs3": vs_doc(V, C, D, "09:00", "10:00", status="cancelled"),
        "vs4": vs_doc(V, C, D2, "20:00", "21:00", tz="Europe/Paris"),
    }
    db.vip_avail.insert_one({"id": f"TEST_i39_av_{uuid.uuid4().hex[:6]}", "vip_id": V, "date": D, "start": "08:00", "end": "23:00",
                             "slot_len": 60, "tz": "America/Toronto", "created_at": datetime.now(timezone.utc).isoformat()})
    yield {"V": V, "Vh": Vh, "C": C, "Ch": Ch, "X": X, "Xh": Xh, **ids}
    for i in (V, C, X):
        db.date_bookings.delete_many({"$or": [{"from_id": i}, {"to_id": i}]})
        db.dates.delete_many({"$or": [{"inviter_id": i}, {"recipient_id": i}]})
        db.vip_sched.delete_many({"$or": [{"vip_id": i}, {"requester_id": i}]})
        db.vip_avail.delete_many({"vip_id": i})
        db.notifications.delete_many({"user_id": i})
        db.users.delete_one({"id": i})


def busy(p, uid, d):
    r = requests.get(f"{API}/profiles/{uid}/availability", headers=p["Xh"], timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["busy_slots"].get(d, [])


def invite(p, to, d, hm, hdr=None):
    return requests.post(f"{API}/invites", headers=hdr or p["Xh"], json={"recipient_id": to, "activity_option_1": "Coffee", "activity_option_2": "Walk",
                         "activity_option_3": "Dinner", "scheduled_start": iso_local(d, hm), "local_day": d, "local_time": hm, "coins": 300, "safety_ack": True}, timeout=30)


# --- availability busy_slots ---
class TestBusySlots:
    def test_vip_and_client_have_vs_block(self, ppl):
        for uid in (ppl["V"], ppl["C"]):
            b = busy(ppl, uid, D)
            hit = [x for x in b if x["from"] == "19:00"]
            assert hit and hit[0] == {"from": "19:00", "to": "21:00", "lock_from": "18:45", "lock_to": "21:15", "reason": "booked"}, b

    def test_pending_and_proposal_locked(self, ppl):
        b = busy(ppl, ppl["V"], D)
        froms = {x["from"]: x for x in b}
        assert "12:00" in froms and froms["12:00"]["lock_from"] == "11:45" and froms["12:00"]["lock_to"] == "13:15"
        assert "15:00" in froms and froms["15:00"]["lock_to"] == "16:15"

    def test_cancelled_not_locked(self, ppl):
        assert not [x for x in busy(ppl, ppl["V"], D) if x["from"] == "09:00"]

    def test_tz_conversion(self, ppl):
        # 20:00 Paris → 14:00 Toronto (Toronto user)
        b = busy(ppl, ppl["C"], D2)
        assert any(x["from"] == "14:00" and x["to"] == "15:00" and x["lock_from"] == "13:45" and x["lock_to"] == "15:15" for x in b), b


# --- regular flows rejected inside VIP calendar locks ---
class TestRegularRejected:
    def test_invite_overlap_vip(self, ppl):
        r = invite(ppl, ppl["V"], D, "21:00")
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_invite_overlap_before_buffer(self, ppl):
        r = invite(ppl, ppl["V"], D, "16:30")  # ends 19:00 > 18:45
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_invite_overlap_client(self, ppl):
        r = invite(ppl, ppl["C"], D, "20:00")
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_invite_overlap_proposal(self, ppl):
        r = invite(ppl, ppl["V"], D, "13:30")  # 13:30-16:00 overlaps proposal lock 14:45-16:15
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_dates_book_overlap(self, ppl):
        r = requests.post(f"{API}/dates/book", headers=ppl["Xh"], json={"target_id": ppl["V"], "venue": "Cafe", "city": "Toronto",
                          "address": "100 Queen St W", "postal_code": "M5H 2N2", "country": "Canada", "address_confirmed": True,
                          "scheduled_at": iso_local(D, "20:00"), "local_day": D, "local_time": "20:00", "coins": 1000,
                          "activities": ["a", "b", "c"]}, timeout=60)
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_vip_pricelist_book_overlap(self, ppl):
        r = requests.post(f"{API}/vip/book", headers=ppl["Xh"], json={"target_id": ppl["V"], "venue": "VIP", "place": "own", "city": "Toronto",
                          "scheduled_at": f"{D}T19:30:00", "coins": 1, "vip_length": 1}, timeout=30)
        if r.status_code == 200:
            db.date_bookings.delete_one({"id": r.json()["booking_id"]})
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, f"VIP price-list booking inside VIP calendar lock accepted: {r.status_code} {r.text}"

    def test_regular_reschedule_into_lock(self, ppl):
        r = invite(ppl, ppl["V"], D3, "12:00")
        assert r.status_code == 200, r.text
        did = r.json()["id"]
        r = requests.post(f"{API}/invites/{did}/reschedule", headers=ppl["Xh"], json={"scheduled_start": iso_local(D, "21:00"), "local_day": D, "local_time": "21:00"}, timeout=30)
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text
        # client side (other party) too: invite C, reschedule into C's lock
        r = invite(ppl, ppl["C"], D3, "12:00")
        assert r.status_code == 200, r.text
        r = requests.post(f"{API}/invites/{r.json()['id']}/reschedule", headers=ppl["Xh"], json={"scheduled_start": iso_local(D, "19:30"), "local_day": D, "local_time": "19:30"}, timeout=30)
        assert r.status_code == 400 and "SLOT_BUSY" in r.text, r.text

    def test_invite_exactly_end_plus_15_allowed(self, ppl):
        r = invite(ppl, ppl["V"], D, "21:15")
        assert r.status_code == 200, r.text
        r = invite(ppl, ppl["C"], D, "16:15")  # ends 18:45 exactly at lock_from
        assert r.status_code == 200, r.text


# --- VIP calendar side ---
class TestVipCalendar:
    def test_taken_lists_locks_and_dates(self, ppl):
        r = requests.get(f"{API}/vip/schedule/{ppl['V']}/slots", headers=ppl["Ch"], timeout=30)
        assert r.status_code == 200, r.text
        dd = next(x for x in r.json()["days"] if x["date"] == D)
        t = dd["taken"]
        vs = [x for x in t if x["from"] == "19:00"]
        assert len(vs) == 1 and vs[0]["lock_from"] == "18:45" and vs[0]["lock_to"] == "21:15" and vs[0]["status"] == "confirmed", t
        assert any(x["from"] == "21:15" and x["status"] == "date" for x in t), t
        assert not any(x["from"] == "09:00" for x in t)

    def test_vs_book_buffer(self, ppl):
        def bk(st, en):
            return requests.post(f"{API}/vip/schedule/{ppl['V']}/book", headers=ppl["Xh"], json={"date": D, "start": st, "end": en,
                                 "coins": 300, "place": "own", "tz": "America/Toronto", "length": 1}, timeout=30)
        r = bk("11:00", "12:00")  # inside vs2 15-min buffer (11:45)
        assert r.status_code == 409 and "SLOT_TAKEN" in r.text, r.text
        r = bk("22:00", "23:00")  # normal invite at 21:15 locks until 24:00
        assert r.status_code == 409 and "SLOT_TAKEN" in r.text, r.text

    def test_vs_reschedule_no_self_conflict(self, ppl):
        # client proposes shifting confirmed vs1 by 30 min — overlaps its own old slot; must not conflict with itself
        r = requests.post(f"{API}/vip/schedule/bookings/{ppl['vs1']}/reschedule", headers=ppl["Ch"], json={"date": D, "start": "19:00", "end": "21:00"}, timeout=30)
        assert r.status_code == 200, r.text
        db.vip_sched.update_one({"id": ppl["vs1"]}, {"$unset": {"reschedule_proposal": ""}})

    def test_vs_pending_reschedule_into_normal_date_409(self, ppl):
        r = requests.post(f"{API}/vip/schedule/bookings/{ppl['vs2']}/reschedule", headers=ppl["Ch"], json={"date": D, "start": "22:00", "end": "23:00"}, timeout=30)
        assert r.status_code == 409 and "SLOT_TAKEN" in r.text, r.text  # invite 21:15 lock until 24:00


# --- cancel frees ---
class TestFreed:
    def test_cancel_frees_slot(self, ppl):
        db.vip_sched.update_one({"id": ppl["vs4"]}, {"$set": {"status": "declined"}})
        assert not [x for x in busy(ppl, ppl["C"], D2) if x["from"] == "14:00"]
        r = invite(ppl, ppl["C"], D2, "14:00")
        assert r.status_code == 200, r.text
