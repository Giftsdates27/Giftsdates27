# Seed (or --clean) VIP calendar bookings for testuser to verify vs-avail-locks UI
import os, sys, uuid, json
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
V, C = "33952702-106f-46d5-86e3-82b490b786c6", "37e28f1d-0f60-4221-ba31-08ffbe32ad8a"
if "--clean" in sys.argv:
    print(db.vip_sched.delete_many({"id": {"$regex": "^TEST_i39ui_"}}).deleted_count); sys.exit()
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
av = db.vip_avail.find_one({"vip_id": V, "date": {"$gt": today}, "start": "18:00"}, sort=[("date", 1)])
d = av["date"] if av else None
if not d:
    d = (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d")
    db.vip_avail.insert_one({"id": "TEST_i39ui_av", "vip_id": V, "date": d, "start": "18:00", "end": "23:00", "slot_len": 60, "tz": "America/Toronto"})
for sid, st, en, stt in (("a", "19:00", "21:00", "confirmed"), ("b", "21:30", "22:30", "pending")):
    db.vip_sched.insert_one({"id": f"TEST_i39ui_{sid}", "vip_id": V, "requester_id": C, "date": d, "start": st, "end": en, "lock_start": "", "lock_end": "",
                             "status": stt, "tz": "America/Toronto", "coins": 300, "hours": 1, "length": 1, "place": "own", "location": {}, "created_at": today})
print(json.dumps({"date": d}))
