import json
import re

from datetime import datetime
from pathlib import Path

import pytest

from tr_rm import config
from tr_rm.cli import process_disruptions
from tr_rm.models import Disruption


@pytest.fixture
def fake_journey():
    return {
        "vehicle_journeys": [{
            "stop_times": [
                {
                    "stop_point": {
                        "name": "Paris - Gare de Lyon - Hall 1 & 2",
                    },
                    "headsign": "7891",
                    "arrival_time": "103900",
                    "departure_time": "103900"
                },
                {
                    "stop_point": {
                        "name": "Lyon Saint-Exupéry TGV",
                    },
                    "headsign": "7891",
                    "arrival_time": "123300",
                    "departure_time": "123700"
                },
            ],
        }]
    }


def test_process_disruptions(httpx_mock, fake_journey):
    s = u = datetime.now()
    # TODO: test pagination (no next in test file)
    disrupt_re = re.compile(fr"{config.BASE_URL}/coverage/sncf/disruptions\?.*")
    with Path("data/disruptions.json").open() as f:
        data = f.read()
    httpx_mock.add_response(url=disrupt_re, json=json.loads(data))

    journeys_re = re.compile(fr"{config.BASE_URL}/coverage/sncf/trips/SNCF:.*")
    with Path("data/vehicle_journeys.json").open() as f:
        data = f.read()
    httpx_mock.add_response(url=journeys_re, json=json.loads(data))

    process_disruptions(s, u)
    ds = [d for d in Disruption.all()]
    assert len(ds) == 16

    # test no duplicates
    process_disruptions(s, u)
    ds = [d for d in Disruption.all()]
    assert len(ds) == 16

    # test updated_at
    with Path("data/disruptions.json").open() as f:
        data = f.read()
        data = json.loads(data)
        did = data["disruptions"][1]["disruption_id"]
        data["disruptions"][1]["updated_at"] = "20230322T144642"
        data["disruptions"][1]["status"] = "fake"
    httpx_mock.add_response(url=disrupt_re, json=data)
    httpx_mock.add_response(url=journeys_re, json=fake_journey)
    process_disruptions(s, u)
    ds = [d for d in Disruption.all()]
    assert len(ds) == 16
    d = Disruption.get(did)
    assert d["status"] == "fake"
    assert d["vehicle_journeys"] == fake_journey["vehicle_journeys"]

    # test number of details request (journeys)
    r_journeys = [r for r in httpx_mock.get_requests() if "vehicle_journeys" in r.url.path]
    # 16 for "stock" + 1 for update
    assert len(r_journeys) == 16 + 1
