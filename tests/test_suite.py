import json
import re

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pytest_httpx import HTTPXMock

from tr_rm import config
from tr_rm.cli import process_disruptions, publish_tomorrow
from tr_rm.models import Disruption


disrupt_re = re.compile(fr"{config.BASE_URL}/coverage/sncf/disruptions\?.*")
journeys_re = re.compile(fr"{config.BASE_URL}/coverage/sncf/trips/SNCF:.*")


@pytest.fixture
def mock_sncf(httpx_mock):
    with Path("data/disruptions.json").open() as f:
        data = f.read()
    httpx_mock.add_response(url=disrupt_re, json=json.loads(data))

    with Path("data/vehicle_journeys.json").open() as f:
        data = f.read()
    httpx_mock.add_response(url=journeys_re, json=json.loads(data))


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


def test_process_disruptions(httpx_mock: HTTPXMock, fake_journey, mock_sncf):
    s = u = datetime.now()
    # TODO: test pagination (no next in test file)
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


def test_publish_tomorrow(httpx_mock: HTTPXMock, mock_sncf):
    httpx_mock.add_response(url=f"https://www.data.gouv.fr/api/1/datasets/{config.DATAGOUVFR_DATASET_ID}/upload/")
    publish_tomorrow()
    request = httpx_mock.get_requests()[-1]
    request.read()
    export_date = datetime.now() + timedelta(days=1)
    date_str = export_date.strftime("%Y%m%d")
    assert f'filename="tr-rm_{date_str}.csv"'.encode("utf-8") in request.content
    assert "x-api-key" in request.headers and request.headers["content-length"] == "254"


def test_publish_tomorrow_fail_429(httpx_mock: HTTPXMock, mock_sncf):
    httpx_mock.add_response(url=journeys_re, status_code=429)
    httpx_mock.add_response(url=f"https://www.data.gouv.fr/api/1/datasets/{config.DATAGOUVFR_DATASET_ID}/upload/")
    publish_tomorrow()
    request = httpx_mock.get_requests()[-1]
    request.read()
    export_date = datetime.now() + timedelta(days=1)
    date_str = export_date.strftime("%Y%m%d")
    assert f'filename="tr-rm_{date_str}-INCOMPLETE.csv"'.encode("utf-8") in request.content
