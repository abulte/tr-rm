import json

from dataclasses import dataclass, InitVar, field
from datetime import datetime, date

from dataset import row_type

from tr_rm import db


class Disruption:
    table_name = "disruptions"
    json_cols = ("application_periods", "impacted_objects", "vehicle_journeys", "messages")

    @classmethod
    @property
    def table(cls):
        return db.table(cls.table_name)

    @classmethod
    def get(cls, _id):
        return cls.table.find_one(disruption_id=_id)

    @classmethod
    def upsert(cls, data):
        data["_id"] = data.pop("id")
        return cls.table.upsert(data, ["disruption_id"], types={c: db.types().json for c in cls.json_cols})

    @classmethod
    def all(cls):
        return cls.table.all()

    @classmethod
    def find(cls, **kwargs):
        return cls.table.find(**kwargs)


@dataclass()
class DisruptionDocument:
    """Serialize a disruption from database in an usable way"""
    data: InitVar[row_type]
    # fields
    departure: str = field(init=False)
    arrival: str = field(init=False)
    departure_time: datetime = field(init=False)
    arrival_time: datetime = field(init=False)
    headsign: str = field(init=False)
    type: str = field(init=False)
    departure_date: date = field(init=False)

    def find_by_kv(self, _list: list, key: str, value):
        """Find an element from a list from a key value"""
        try:
            return next((x for x in _list if x[key] == value))
        except StopIteration:
            pass

    def format_time(self, time_str: str):
        """"103900" -> [10, 39, 00]"""
        return [int(x) for x in (time_str[0:2], time_str[2:4], time_str[4:6])]

    def __post_init__(self, data: row_type):
        # TODO: handle multiple journeys?
        journey = json.loads(data["vehicle_journeys"])[0]
        full_type = self.find_by_kv(journey["codes"], "type", "rt_piv")["value"]
        self.type = ":".join(full_type.split(":")[-2:])
        stops = journey["stop_times"]
        departure = stops[0]
        arrival = stops[-1]
        self.departure = departure["stop_point"]["name"]
        self.arrival = arrival["stop_point"]["name"]
        self.headsign = departure["headsign"]
        periods = json.loads(data["application_periods"])[0]
        fmt = "%Y%m%dT%H%M%S"
        self.departure_time = datetime.strptime(periods["begin"], fmt)
        self.arrival_time = datetime.strptime(periods["end"], fmt)
        h, m, s = self.format_time(departure["departure_time"])
        self.departure_time.replace(hour=h, minute=m, second=s)
        self.departure_date = self.departure_time.date()
        h, m, s = self.format_time(arrival["arrival_time"])
        self.arrival_time.replace(hour=h, minute=m, second=s)
