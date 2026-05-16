#!/usr/bin/env python3
"""
macOS telemetry daemon (fixed delegate definition):
- Battery %
- CoreLocation -> CLGeocoder (city/region/country)
- Timestamp
- Upsert single rolling doc in MongoDB (_id='current')
"""

import os, sys, time, json, uuid, platform, subprocess, re, datetime
from typing import Optional, Dict

# ----------------------- .env loader -----------------------------------------
def load_dotenv(path: str = ".env"):
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(path)
        return
    except Exception:
        pass
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

# ----------------------- Config ---------------------------------------------
SAMPLE_EVERY_SEC = int(os.environ.get("SAMPLE_EVERY_SEC", "120"))
DB_NAME   = os.environ.get("MONGO_DB", "system_monitor")
COLL_NAME = os.environ.get("MONGO_COLLECTION", "telemetry")
DOC_ID    = os.environ.get("DOC_ID", "current")
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")

# ----------------------- Battery --------------------------------------------
def battery_psutil() -> Optional[float]:
    try:
        import psutil  # type: ignore
        b = psutil.sensors_battery()
        if b and b.percent is not None:
            return float(b.percent)
    except Exception:
        pass
    return None

def battery_pmset() -> Optional[float]:
    try:
        out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
        m = re.search(r"(\d+)%", out)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None

def get_battery_percent() -> Optional[float]:
    return battery_psutil() or battery_pmset()

# ----------------------- CoreLocation setup (define delegate ONCE) ----------
try:
    from Foundation import NSObject, NSRunLoop, NSDate
    from CoreLocation import CLLocationManager, CLLocation, CLGeocoder
    _PYOBJC_AVAILABLE = True
except Exception:
    _PYOBJC_AVAILABLE = False

# Define the Objective-C bridged class once to avoid "overriding existing class"
TelemetryLocationDelegate = None
if _PYOBJC_AVAILABLE:
    class _TelemetryLocationDelegate(NSObject):  # unique name at module scope
        def init(self):
            return super().init()

        def locationManagerDidChangeAuthorization_(self, manager):
            # 3=AuthorizedAlways, 4=AuthorizedWhenInUse, 2=Denied
            try:
                status = manager.authorizationStatus()
                if status in (3, 4):
                    manager.startUpdatingLocation()
                elif status == 2:
                    # Denied; signal via attached state dict
                    state = getattr(self, "_state", None)
                    if state is not None:
                        state["done"] = True
            except Exception:
                state = getattr(self, "_state", None)
                if state is not None:
                    state["done"] = True

        def locationManager_didUpdateLocations_(self, manager, locations):
            try:
                state = getattr(self, "_state", None)
                if state is None:
                    manager.stopUpdatingLocation()
                    return
                loc = locations[-1]
                coord = loc.coordinate()
                hacc = getattr(loc, "horizontalAccuracy", None)
                state["val"] = {
                    "lat": float(coord.latitude),
                    "lon": float(coord.longitude),
                    "hacc": float(hacc()) if callable(hacc) else None,
                }
            except Exception:
                pass
            finally:
                manager.stopUpdatingLocation()
                state = getattr(self, "_state", None)
                if state is not None:
                    state["done"] = True

        def locationManager_didFailWithError_(self, manager, error):
            state = getattr(self, "_state", None)
            if state is not None:
                state["done"] = True

    TelemetryLocationDelegate = _TelemetryLocationDelegate  # alias

def corelocation_latlon(timeout_sec: float = 8.0) -> Optional[Dict]:
    """Return {'lat','lon','hacc'} via CoreLocation or None."""
    if not _PYOBJC_AVAILABLE:
        return None
    try:
        state = {"done": False, "val": None}
        mgr = CLLocationManager.alloc().init()
        delegate = TelemetryLocationDelegate.alloc().init()
        # attach state so delegate methods can update it
        setattr(delegate, "_state", state)
        mgr.setDelegate_(delegate)

        if hasattr(mgr, "requestWhenInUseAuthorization"):
            mgr.requestWhenInUseAuthorization()
        if hasattr(mgr, "authorizationStatus") and mgr.authorizationStatus() in (3, 4):
            mgr.startUpdatingLocation()

        deadline = time.time() + timeout_sec
        while time.time() < deadline and not state["done"]:
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))

        return state["val"]
    except Exception:
        return None

def reverse_geocode_city(lat: float, lon: float, timeout_sec: float = 8.0) -> Optional[Dict]:
    """Use CLGeocoder to reverse-geocode to city/region/country/postal."""
    if not _PYOBJC_AVAILABLE:
        return None
    try:
        done = {"flag": False, "val": None}
        loc = CLLocation.alloc().initWithLatitude_longitude_(lat, lon)
        geocoder = CLGeocoder.alloc().init()

        def handler(placemarks, error):
            try:
                result = {"city": None, "region": None, "country": None, "postal": None}
                if placemarks and len(placemarks) > 0:
                    pm = placemarks[0]
                    # these may be None depending on locale/data
                    try: result["city"]   = pm.locality()
                    except Exception: pass
                    try: result["region"] = pm.administrativeArea()
                    except Exception: pass
                    try: result["country"]= pm.country()
                    except Exception: pass
                    try: result["postal"] = pm.postalCode()
                    except Exception: pass
                done["val"] = result
            finally:
                done["flag"] = True

        geocoder.reverseGeocodeLocation_completionHandler_(loc, handler)

        deadline = time.time() + timeout_sec
        while time.time() < deadline and not done["flag"]:
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))

        return done["val"]
    except Exception:
        return None

# ----------------------- IP fallback (optional) ------------------------------
def ip_location_city() -> Optional[Dict]:
    try:
        import urllib.request
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=4) as resp:
            info = json.loads(resp.read().decode("utf-8"))
        out = {
            "city": info.get("city"),
            "region": info.get("region"),
            "country": info.get("country"),
            "postal": None,
        }
        if "loc" in info:
            lat_str, lon_str = info["loc"].split(",")
            out["lat"] = float(lat_str)
            out["lon"] = float(lon_str)
        return out
    except Exception:
        return None

def get_location_with_city() -> Optional[Dict]:
    latlon = corelocation_latlon(timeout_sec=8.0)
    if latlon:
        geo = reverse_geocode_city(latlon["lat"], latlon["lon"], timeout_sec=8.0) or {}
        return {
            "city":   geo.get("city"),
            "region": geo.get("region"),
            "country":geo.get("country"),
            "postal": geo.get("postal"),
            "lat":    latlon["lat"],
            "lon":    latlon["lon"],
            "hacc":   latlon.get("hacc"),
            "source": "corelocation+clgeocoder",
        }
    ip = ip_location_city()
    if ip:
        ip["source"] = "ipinfo"
        return ip
    return None

# ----------------------- Mongo ----------------------------------------------
def mongo_client():
    from pymongo import MongoClient  # type: ignore
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)

def write_single(doc: Dict):
    client = mongo_client()
    try:
        coll = client[DB_NAME][COLL_NAME]
        coll.replace_one({"_id": DOC_ID}, {"_id": DOC_ID, **doc}, upsert=True)
    finally:
        client.close()

# ----------------------- Snapshot + Loop ------------------------------------
def snapshot() -> Dict:
    now_iso = datetime.datetime.now().astimezone().isoformat()
    return {
        "timestamp": now_iso,
        "device": {
            "hostname": platform.node(),
            "model": platform.platform(),
            "id_hint": str(uuid.getnode()),
        },
        "battery": {"percent": get_battery_percent()},
        "location": get_location_with_city(),
        "notes": "Single rolling document; delegate defined once at module scope.",
    }

def main():
    if platform.system() != "Darwin":
        print("Warning: intended for macOS (Darwin).", file=sys.stderr)

    while True:
        try:
            write_single(snapshot())
        except Exception as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[telemetry] error [{ts}]: {e}", file=sys.stderr)
        time.sleep(SAMPLE_EVERY_SEC)

if __name__ == "__main__":
    main()