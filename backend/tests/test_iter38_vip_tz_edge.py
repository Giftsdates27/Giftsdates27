# Iteration 38 edge: VIP price-list wall-clock times are compared as if UTC (VIP in a non-UTC tz)
import uuid, requests, pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from test_iter38_tz_vip_resched import API, db, mk


@pytest.fixture(scope="module")
def la():
    vip_until = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    C, Ch = mk("ec", "TEST EClient", {"timezone": "America/Sao_Paulo"})
    V, Vh = mk("ev", "TEST EVip", {"timezone": "America/Sao_Paulo", "vip_until": vip_until,
                                   "vip": {"prices": {"hour": 300, "h2": 500, "h3": 700, "extra": 250}}})
    yield {"C": C, "Ch": Ch, "V": V, "Vh": Vh}
    for i in (C, V):
        db.date_bookings.delete_many({"$or": [{"from_id": i}, {"to_id": i}]})
        db.users.delete_one({"id": i})


def test_propose_later_today_in_vip_clock(la):
    now_la = datetime.now(ZoneInfo("America/Sao_Paulo"))
    tgt = (now_la + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    if tgt.date() != now_la.date(): pytest.skip("time of day not suitable")
    d = (now_la + timedelta(days=2)).strftime("%Y-%m-%d")
    r = requests.post(f"{API}/vip/book", headers=la["Ch"], json={"target_id": la["V"], "venue": "VIP", "place": "own", "city": "LA",
                                                               "scheduled_at": f"{d}T12:00:00", "coins": 1, "vip_length": 1})
    bid = r.json()["booking_id"]
    day_s, hm = tgt.strftime("%Y-%m-%d"), tgt.strftime("%H:%M")
    r = requests.post(f"{API}/dates/reschedule/{bid}", headers=la["Ch"], json={"scheduled_start": f"{day_s}T{hm}:00", "local_day": day_s, "local_time": hm})
    print("propose", day_s, hm, "LA ->", r.status_code, r.text)
    assert r.status_code == 200, f"Valid future LA wall-clock time rejected: {r.text}"


def test_past_time_today_in_vip_clock_rejected(la):
    db.users.update_one({"id": la["V"]}, {"$set": {"timezone": "Asia/Tokyo"}})
    now_tk = datetime.now(ZoneInfo("Asia/Tokyo"))
    past = (now_tk - timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
    if past.date() != now_tk.date() or past.hour < 9 - 0: pytest.skip("time of day not suitable")
    if (past.hour * 60) <= datetime.now(timezone.utc).hour * 60 + datetime.now(timezone.utc).minute: pytest.skip("naive==utc also past")
    d = (now_tk + timedelta(days=2)).strftime("%Y-%m-%d")
    bid = requests.post(f"{API}/vip/book", headers=la["Ch"], json={"target_id": la["V"], "venue": "VIP", "place": "own", "city": "Tokyo",
                        "scheduled_at": f"{d}T12:00:00", "coins": 1, "vip_length": 1}).json()["booking_id"]
    day_s, hm = past.strftime("%Y-%m-%d"), past.strftime("%H:%M")
    r = requests.post(f"{API}/dates/reschedule/{bid}", headers=la["Ch"], json={"scheduled_start": f"{day_s}T{hm}:00", "local_day": day_s, "local_time": hm})
    print("past propose", day_s, hm, "Tokyo ->", r.status_code, r.text)
    assert r.status_code == 400, f"Past Tokyo wall-clock time accepted: {r.text}"
