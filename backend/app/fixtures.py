from .schemas import Candidate, OpenPeriod

def lisbon_candidates() -> list[Candidate]:
    def hrs(open_h, close_h, days=range(7)):
        return [OpenPeriod(open_day=d, open_h=open_h, open_m=0, close_day=d, close_h=close_h, close_m=0)
                for d in days]

    raw = [
        # ref filled in below; (name, category, lat, lng, rating, rating_count, price_level, duration, hours)
        ("Belem Tower", "attraction", 38.6916, -9.2160, 4.5, 45000, 1, 60, hrs(10, 17, [1,2,3,4,5,6])),  # closed Mon
        ("Jeronimos Monastery", "attraction", 38.6979, -9.2068, 4.7, 52000, 2, 90, hrs(10, 17, [1,2,3,4,5,6])),
        ("Sao Jorge Castle", "attraction", 38.7139, -9.1335, 4.6, 38000, 2, 75, hrs(9, 21)),
        "SEP",
        ("Pasteis de Belem", "food", 38.6975, -9.2032, 4.5, 30000, 1, 30, hrs(8, 23)),
        ("Time Out Market", "food", 38.7069, -9.1459, 4.4, 60000, 2, 60, hrs(10, 24)),
        ("Cervejaria Ramiro", "food", 38.7225, -9.1360, 4.6, 25000, 3, 75, hrs(12, 24, [1,2,3,4,5,6])),
        ("A Cevicheria", "food", 38.7167, -9.1477, 4.5, 8000, 3, 60, hrs(12, 23)),
        ("Confeitaria Nacional", "food", 38.7139, -9.1389, 4.4, 5000, 1, 30, hrs(8, 20, [0,1,2,3,4,5])),
        ("Alfama Old Town Walk", "nature", 38.7126, -9.1305, 4.6, 12000, 0, 90, hrs(0, 24)),
        ("Miradouro da Graca", "nature", 38.7161, -9.1305, 4.5, 15000, 0, 45, hrs(0, 24)),
        ("LX Factory", "shopping", 38.7043, -9.1783, 4.5, 22000, 1, 90, hrs(10, 22)),
        ("Fado Museum", "attraction", 38.7117, -9.1301, 4.3, 3000, 1, 60, hrs(10, 18, [1,2,3,4,5,6])),
        ("Pink Street Nightlife", "nightlife", 38.7069, -9.1435, 4.2, 9000, 2, 120, hrs(20, 3)),
    ]
    out = []
    i = 0
    for row in raw:
        if row == "SEP":
            continue
        name, cat, lat, lng, rating, rc, price, dur, periods = row
        i += 1
        out.append(Candidate(ref=f"c{i}", place_id=f"FIX_{i}", name=name, category=cat,
                             lat=lat, lng=lng, rating=rating, rating_count=rc, price_level=price,
                             typical_duration_min=dur, open_periods=periods,
                             sources=["fixture"]))
    return out