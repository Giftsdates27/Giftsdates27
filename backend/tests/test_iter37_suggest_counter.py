# Iteration 37: VIP suggest endpoint, client counter-offer, regular invite/booking quick-time suggestions
import json, subprocess, sys, requests, pytest
from datetime import datetime, timedelta, timezone
sys.path.insert(0, "/app/backend/tests")
from seed_iter37 import API, db, seed


@pytest.fixture(scope="module")
def S():
    s = seed()
    def h(k):
        r = requests.post(f"{API}/auth/login", json={"email": s[k][0], "password": s[k][1]}).json()
        return {"Authorization": f"Bearer {r['token']}"}
    s["h"] = {k: h(k) for k in ("A", "V", "R", "I")}
    return s


def sug(url, h):
    r = requests.get(f"{API}{url}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["suggestions"]


def vb(bid):
    return db.vip_sched.find_one({"id": bid}, {"_id": 0})


# ---- VIP suggest endpoint ----
class TestVipSuggest:
    def test_access(self, S):
        for k in ("A", "V"):
            assert requests.get(f"{API}/vip/schedule/bookings/{S['pending']}/suggest", headers=S["h"][k]).status_code == 200
        assert requests.get(f"{API}/vip/schedule/bookings/{S['pending']}/suggest", headers=S["h"]["R"]).status_code == 403
        assert requests.get(f"{API}/vip/schedule/bookings/nope/suggest", headers=S["h"]["A"]).status_code == 404

    def test_excludes_current_and_proposal_same_length_in_avail(self, S):
        for k in ("pending", "confirmed", "pending2", "confirmed2"):
            b = vb(k and S[k]); p = b.get("reschedule_proposal") or {}
            out = sug(f"/vip/schedule/bookings/{S[k]}/suggest", S["h"]["A"])
            assert 1 <= len(out) <= 3
            for s in out:
                assert not (s["date"] == b["date"] and s["start"] == b["start"])
                assert not (s["date"] == p.get("date") and s["start"] == p.get("start"))
                sm = int(s["start"][:2]) * 60 + int(s["start"][3:]); em = int(s["end"][:2]) * 60 + int(s["end"][3:])
                assert em - sm == 60 and sm >= 600 and em <= 960

    def test_proposals_count_as_busy(self, S):
        # pending2's VIP proposal (day3 10:00-11:00) must block 10:00 for the other pending booking
        out = sug(f"/vip/schedule/bookings/{S['pending']}/suggest", S["h"]["A"])
        assert all(s["start"] != "10:00" for s in out if s["date"] == vb(S["pending2"])["date"])


# ---- Client counter-offer ----
class TestCounterOffer:
    def test_confirmed_counter_replaces_proposal_by_client(self, S):
        bid = S["confirmed2"]; old = vb(bid)
        assert old["reschedule_proposal"]["by"] == "vip"
        s = sug(f"/vip/schedule/bookings/{bid}/suggest", S["h"]["A"])[0]
        r = requests.post(f"{API}/vip/schedule/bookings/{bid}/reschedule", headers=S["h"]["A"], json={k: s[k] for k in ("date", "start", "end")})
        assert r.status_code == 200, r.text
        b = vb(bid)
        assert b["status"] == "confirmed" and b["start"] == old["start"]
        assert b["reschedule_proposal"]["by"] == "client" and b["reschedule_proposal"]["start"] == s["start"]
        # client cannot accept own proposal; VIP can counter back
        assert requests.post(f"{API}/vip/schedule/bookings/{bid}/reschedule/accept", headers=S["h"]["A"]).status_code == 403
        vs = sug(f"/vip/schedule/bookings/{bid}/suggest", S["h"]["V"])
        assert vs and all(x["start"] != s["start"] or x["date"] != s["date"] for x in vs)
        r = requests.post(f"{API}/vip/schedule/bookings/{bid}/reschedule", headers=S["h"]["V"], json={k: vs[0][k] for k in ("date", "start", "end")})
        assert r.status_code == 200 and vb(bid)["reschedule_proposal"]["by"] == "vip"

    def test_pending_counter_changes_time_instantly(self, S):
        bid = S["pending2"]
        s = sug(f"/vip/schedule/bookings/{bid}/suggest", S["h"]["A"])[0]
        r = requests.post(f"{API}/vip/schedule/bookings/{bid}/reschedule", headers=S["h"]["A"], json={k: s[k] for k in ("date", "start", "end")})
        assert r.status_code == 200, r.text
        b = vb(bid)
        assert b["status"] == "pending" and b["start"] == s["start"] and b["date"] == s["date"]
        assert "reschedule_proposal" not in b


# ---- Regular invite/booking suggestions ----
def _check_regular(out, cur_day, cur_time, offset_h):
    now = datetime.now(timezone.utc)
    assert 1 <= len(out) <= 3
    for s in out:
        assert not (s["date"] == cur_day and s["start"] == cur_time)
        assert "18:00" <= s["start"] and s["start"] <= "20:30"
        sm = int(s["start"][:2]) * 60 + int(s["start"][3:]); em = int(s["end"][:2]) * 60 + int(s["end"][3:])
        assert em - sm == 150
        st = datetime.fromisoformat(s["scheduled_start"])
        assert st >= now + timedelta(hours=1)
        local = datetime.fromisoformat(f"{s['date']}T{s['start']}:00").replace(tzinfo=timezone.utc)
        assert local - st == timedelta(hours=offset_h)


class TestRegularSuggest:
    def test_access(self, S):
        assert requests.get(f"{API}/invites/{S['invite']}/suggest", headers=S["h"]["A"]).status_code == 403
        assert requests.get(f"{API}/dates/suggest/{S['booking']}", headers=S["h"]["A"]).status_code == 403
        assert requests.get(f"{API}/invites/{S['invite']}/suggest", headers=S["h"]["I"]).status_code == 200

    def test_invite_suggest_offset_and_rules(self, S):
        d = db.dates.find_one({"id": S["invite"]})
        out = sug(f"/invites/{S['invite']}/suggest", S["h"]["R"])
        _check_regular(out, d["local_day"], d["local_time"], -5)
        # booking day (day3 19:00) is busy for both -> no 18:00 on that day
        bday = db.date_bookings.find_one({"id": S["booking"]})["local_day"]
        assert all(s["date"] != bday for s in out)

    def test_booking_suggest(self, S):
        b = db.date_bookings.find_one({"id": S["booking"]})
        out = sug(f"/dates/suggest/{S['booking']}", S["h"]["R"])
        _check_regular(out, b["local_day"], b["local_time"], 0)
        iday = db.dates.find_one({"id": S["invite"]})["local_day"]
        assert all(s["date"] != iday for s in out)

    def test_pick_invite_suggestion_creates_proposal_not_cancel(self, S):
        s = sug(f"/invites/{S['invite']}/suggest", S["h"]["R"])[0]
        r = requests.post(f"{API}/invites/{S['invite']}/reschedule", headers=S["h"]["R"],
                          json={"scheduled_start": s["scheduled_start"], "local_day": s["date"], "local_time": s["start"]})
        assert r.status_code == 200, r.text
        d = db.dates.find_one({"id": S["invite"]})
        assert d["status"] == "INVITATION_SENT" and d["reschedule_proposal"]["local_time"] == s["start"]

    def test_pending_proposal_blocks_booking_suggest(self, S):
        p = db.dates.find_one({"id": S["invite"]})["reschedule_proposal"]
        out = sug(f"/dates/suggest/{S['booking']}", S["h"]["R"])
        assert all(not (s["date"] == p["local_day"] and s["start"] == p["local_time"]) for s in out)

    def test_pick_booking_suggestion_creates_proposal(self, S):
        s = sug(f"/dates/suggest/{S['booking']}", S["h"]["R"])[0]
        r = requests.post(f"{API}/dates/reschedule/{S['booking']}", headers=S["h"]["R"],
                          json={"scheduled_start": s["scheduled_start"], "local_day": s["date"], "local_time": s["start"]})
        assert r.status_code == 200, r.text
        b = db.date_bookings.find_one({"id": S["booking"]})
        assert b["status"] == "escrow" and b["reschedule_proposal"]["local_time"] == s["start"]
