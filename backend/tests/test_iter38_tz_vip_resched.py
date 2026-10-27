# Iteration 38: timezone labels (user tz exposure) + VIP price-list booking reschedule/suggest
import os, uuid, requests, pytest
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env"); load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PW = "Test@12345"


def day(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).strftime("%Y-%m-%d")


def mk(key, name, extra=None):
    email = f"test_i38_{key}_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name, "age": 29, "gender": "male",
                                                  "interested_in": "female", "city": "Paris", "country": "France"})
    assert r.status_code == 200, r.text
    r = r.json()
    s = {"coins": 50000, "email_verified": True, "onboarded": True}
    if extra: s.update(extra)
    db.users.update_one({"id": r["user"]["id"]}, {"$set": s})
    return r["user"]["id"], {"Authorization": f"Bearer {r['token']}"}


@pytest.fixture(scope="module")
def ppl():
    vip_until = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    C, Ch = mk("c", "TEST Client", {"timezone": "America/Toronto"})
    V, Vh = mk("v", "TEST Vip", {"timezone": "Europe/Paris", "vip_until": vip_until,
                                 "vip": {"prices": {"hour": 300, "h2": 500, "h3": 700, "extra": 250}}})
    yield {"C": C, "Ch": Ch, "V": V, "Vh": Vh}
    for i in (C, V):
        db.date_bookings.delete_many({"$or": [{"from_id": i}, {"to_id": i}]})
        db.dates.delete_many({"$or": [{"inviter_id": i}, {"recipient_id": i}]})
        db.users.delete_one({"id": i})


def vipbook(p, n=3, hm="12:00", length=2):
    r = requests.post(f"{API}/vip/book", headers=p["Ch"], json={"target_id": p["V"], "venue": "VIP", "place": "own", "city": "Paris",
                                                              "scheduled_at": f"{day(n)}T{hm}:00", "coins": 1, "vip_length": length})
    assert r.status_code == 200, r.text
    return r.json()["booking_id"]


# --- timezone on profile ---
class TestTimezonePatch:
    def test_valid_tz_saved(self, ppl):
        r = requests.patch(f"{API}/auth/me", headers=ppl["Ch"], json={"timezone": "Asia/Tokyo"})
        assert r.status_code == 200, r.text
        assert requests.get(f"{API}/auth/me", headers=ppl["Ch"]).json()["timezone"] == "Asia/Tokyo"

    def test_invalid_tz_ignored(self, ppl):
        for bad in ("Mars/Olympus", "../etc/passwd", "not a tz"):
            r = requests.patch(f"{API}/auth/me", headers=ppl["Ch"], json={"timezone": bad})
            assert r.status_code == 200, r.text
        assert requests.get(f"{API}/auth/me", headers=ppl["Ch"]).json()["timezone"] == "Asia/Tokyo"
        requests.patch(f"{API}/auth/me", headers=ppl["Ch"], json={"timezone": "America/Toronto"})


# --- tz exposure in listings ---
class TestTzExposure:
    def test_dates_other_tz(self, ppl):
        bid = vipbook(ppl, 5, "13:00", 1)
        out = requests.get(f"{API}/dates", headers=ppl["Ch"]).json()["outgoing"]
        row = next(b for b in out if b["id"] == bid)
        assert row["other_tz"] == "Europe/Paris"
        inc = requests.get(f"{API}/dates", headers=ppl["Vh"]).json()["incoming"]
        row = next(b for b in inc if b["id"] == bid)
        assert row["other_tz"] == "America/Toronto"

    def test_invite_other_tz(self, ppl):
        st = datetime.now(timezone.utc).replace(microsecond=0, second=0, minute=0) + timedelta(days=6)
        r = requests.post(f"{API}/invites", headers=ppl["Ch"], json={"recipient_id": ppl["V"], "activity_option_1": "Coffee", "activity_option_2": "Walk",
                          "activity_option_3": "Dinner", "scheduled_start": st.isoformat(), "local_day": st.strftime("%Y-%m-%d"),
                          "local_time": st.strftime("%H:%M"), "coins": 300, "safety_ack": True})
        if r.status_code != 200: pytest.skip(f"invite create failed: {r.text}")
        did = r.json()["id"]
        out = requests.get(f"{API}/invites", headers=ppl["Ch"]).json()["outgoing"]
        assert next(d for d in out if d["id"] == did)["other"]["tz"] == "Europe/Paris"
        inc = requests.get(f"{API}/invites", headers=ppl["Vh"]).json()["incoming"]
        assert next(d for d in inc if d["id"] == did)["other"]["tz"] == "America/Toronto"


# --- VIP price-list reschedule ---
class TestVipPriceListReschedule:
    def test_propose_and_accept(self, ppl):
        bid = vipbook(ppl, 3, "12:00", 2)
        b0 = db.date_bookings.find_one({"id": bid})
        assert b0["duration_min"] == 120 and b0["slot_from"] == "12:00" and b0["slot_to"] == "14:00"
        r = requests.post(f"{API}/dates/reschedule/{bid}", headers=ppl["Ch"],
                          json={"scheduled_start": f"{day(4)}T15:30:00", "local_day": day(4), "local_time": "15:30"})
        assert r.status_code == 200, r.text
        assert r.json()["proposal"]["scheduled_start"] == f"{day(4)}T15:30:00"
        # proposer cannot accept own
        assert requests.post(f"{API}/dates/reschedule/{bid}/accept", headers=ppl["Ch"]).status_code == 403
        r = requests.post(f"{API}/dates/reschedule/{bid}/accept", headers=ppl["Vh"])
        assert r.status_code == 200, r.text
        b = db.date_bookings.find_one({"id": bid}, {"_id": 0})
        assert b["scheduled_at"] == f"{day(4)}T15:30:00"
        assert b["local_day"] == day(4) and b["local_time"] == "15:30"
        assert b["slot_from"] == "15:30" and b["slot_to"] == "17:30"
        assert "reschedule_proposal" not in b

    def test_vip_side_proposes_normalized_wallclock(self, ppl):
        bid = vipbook(ppl, 7, "11:00", 1)
        r = requests.post(f"{API}/dates/reschedule/{bid}", headers=ppl["Vh"],
                          json={"scheduled_start": f"{day(7)}T13:00:00+01:00", "local_day": day(7), "local_time": "13:00"})
        assert r.status_code == 200, r.text
        assert r.json()["proposal"]["scheduled_start"] == f"{day(7)}T13:00:00"
        assert requests.post(f"{API}/dates/reschedule/{bid}/decline", headers=ppl["Ch"]).json()["status"] == "declined"
        b = db.date_bookings.find_one({"id": bid}, {"_id": 0})
        assert b["scheduled_at"] == f"{day(7)}T11:00:00" and "reschedule_proposal" not in b

    def test_suggest_vip(self, ppl):
        bid = vipbook(ppl, 8, "12:00", 3)
        r = requests.get(f"{API}/dates/suggest/{bid}", headers=ppl["Vh"])
        assert r.status_code == 200, r.text
        sg = r.json()["suggestions"]
        assert len(sg) >= 1
        for s in sg:
            assert s["scheduled_start"] == f"{s['date']}T{s['start']}:00"
            sm = int(s["start"][:2]) * 60 + int(s["start"][3:]); em = int(s["end"][:2]) * 60 + int(s["end"][3:])
            assert (em - sm) % 1440 == 180, s
            assert not (s["date"] == day(8) and s["start"] == "12:00")
        # tapping a chip = POST proposal with the suggestion
        s = sg[0]
        r = requests.post(f"{API}/dates/reschedule/{bid}", headers=ppl["Vh"], json={"scheduled_start": s["scheduled_start"], "local_day": s["date"], "local_time": s["start"]})
        assert r.status_code == 200, r.text
        assert db.date_bookings.find_one({"id": bid})["reschedule_proposal"]["local_time"] == s["start"]

    def test_suggest_respects_length_in_window(self, ppl):
        # VIP with availability 18:00-21:00 on day 9 only -> a 3h booking has exactly one fit (18:00)
        db.users.update_one({"id": ppl["V"]}, {"$set": {"availability_ranges": {day(9): [{"from": "18:00", "to": "21:00"}], day(10): [{"from": "18:00", "to": "20:00"}]}}})
        try:
            bid = db.date_bookings.insert_one({"id": str(uuid.uuid4()), "from_id": ppl["C"], "to_id": ppl["V"], "venue": "VIP", "city": "Paris", "place": "own",
                                               "scheduled_at": f"{day(9)}T18:00:00", "coins": 700, "duration_min": 180, "vip_length": 3, "local_day": day(9),
                                               "slot_from": "18:00", "slot_to": "21:00", "status": "escrow", "vip": True,
                                               "created_at": datetime.now(timezone.utc).isoformat()}).inserted_id
            b = db.date_bookings.find_one({"_id": bid})
            r = requests.get(f"{API}/dates/suggest/{b['id']}", headers=ppl["Ch"])
            assert r.status_code == 200, r.text
            assert r.json()["suggestions"] == [], r.json()  # the only 3h fit is the current one; 2h window on day 10 cannot hold 3h
            r = requests.post(f"{API}/dates/reschedule/{b['id']}", headers=ppl["Ch"], json={"scheduled_start": f"{day(10)}T18:00:00", "local_day": day(10), "local_time": "18:00"})
            assert r.status_code == 400 and "TIME_UNAVAILABLE" in r.text, r.text
        finally:
            db.users.update_one({"id": ppl["V"]}, {"$unset": {"availability_ranges": ""}})

    def test_no_cannot_reschedule_for_vip(self, ppl):
        bid = vipbook(ppl, 11, "10:00", 1)
        r = requests.post(f"{API}/dates/reschedule/{bid}", headers=ppl["Ch"], json={"scheduled_start": f"{day(11)}T16:00:00", "local_day": day(11), "local_time": "16:00"})
        assert r.status_code == 200 and "CANNOT_RESCHEDULE" not in r.text


# --- regression: regular booking reschedule + suggestions ---
class TestRegularRegression:
    def test_regular_booking_resched(self, ppl):
        st = datetime.fromisoformat(f"{day(12)}T19:00:00+00:00")
        r = requests.post(f"{API}/dates/book", headers=ppl["Ch"], json={"target_id": ppl["V"], "venue": "TEST Cafe", "city": "Paris", "scheduled_at": st.isoformat(),
                          "local_day": day(12), "local_time": "19:00", "coins": 300, "address_confirmed": True, "address": "1 Rue", "postal_code": "75001",
                          "country": "France", "activities": ["Coffee", "Walk", "Dinner"]})
        assert r.status_code == 200, r.text
        bid = r.json()["booking_id"]
        sg = requests.get(f"{API}/dates/suggest/{bid}", headers=ppl["Vh"]).json()["suggestions"]
        assert sg and all(s["scheduled_start"].endswith("+00:00") or "Z" in s["scheduled_start"] for s in sg), sg
        s = sg[0]
        r = requests.post(f"{API}/dates/reschedule/{bid}", headers=ppl["Vh"], json={"scheduled_start": s["scheduled_start"], "local_day": s["date"], "local_time": s["start"]})
        assert r.status_code == 200, r.text
        assert requests.post(f"{API}/dates/reschedule/{bid}/accept", headers=ppl["Ch"]).status_code == 200
        b = db.date_bookings.find_one({"id": bid})
        assert b["local_time"] == s["start"] and b["scheduled_at"].startswith(s["date"])
