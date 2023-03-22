import logging

from datetime import datetime, timedelta

import httpx

from minicli import cli, run
from tabulate import tabulate

from tr_rm import config
from tr_rm.db import query
from tr_rm.models import Disruption, DisruptionDocument

HEADERS = {"Authorization": config.SNCF_API_KEY}
BASE_URL = config.BASE_URL

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("tr_rm")


def process_disruptions(since: datetime, until: datetime, effects=["NO_SERVICE"]):
    def _get(url: str):
        r = httpx.get(url, headers=HEADERS, params={
            "since": since.isoformat(),
            "until": until.isoformat(),
        })
        r.raise_for_status()
        data = r.json()
        next_url = [link["href"] for link in data["links"] if link["type"] == "next"]
        return data["disruptions"], next_url[0] if next_url else None
    disruptions = []
    next_url = f"{BASE_URL}/coverage/sncf/disruptions"
    while next_url:
        res, next_url = _get(next_url)
        disruptions += res
    filtered_disruptions = [d for d in disruptions if d["severity"]["effect"] in effects]
    filtered_disruptions = enrich_disruptions(filtered_disruptions)
    return filtered_disruptions


def enrich_disruptions(disruptions: list):
    for disrupt in disruptions:
        existing = Disruption.get(disrupt["disruption_id"])
        if not existing or existing["updated_at"] != disrupt["updated_at"]:
            pt = disrupt["impacted_objects"][0]["pt_object"]
            if not pt["embedded_type"] == "trip":
                log.warning(f"PT type is {pt['type']} for disruption {disrupt['disruption_id']}")
                continue
            url = f"{BASE_URL}/coverage/sncf/trips/{pt['id']}/vehicle_journeys?disable_disruption=true"
            r = httpx.get(url, headers=HEADERS)
            r.raise_for_status()
            journeys = r.json()["vehicle_journeys"]
            disrupt["vehicle_journeys"] = journeys
            Disruption.upsert(disrupt)
        else:
            disrupt["vehicle_journeys"] = existing["vehicle_journeys"]
    return disruptions


@cli
def last_hour():
    since = datetime.now() - timedelta(hours=1)
    until = datetime.now()
    process_disruptions(since, until)


@cli
def last_day():
    since = datetime.now() - timedelta(days=1)
    until = datetime.now()
    process_disruptions(since, until)


@cli
def next_day():
    since = datetime.now()
    until = datetime.now() + timedelta(days=1)
    process_disruptions(since, until)


@cli
def display():
    q = """
    SELECT * FROM disruptions
    ORDER BY application_periods->'0'->'begin' ASC
    """
    ds = query(q)
    ds = [DisruptionDocument(d).__dict__ for d in ds]
    print(tabulate(ds, headers="keys"))


if __name__ == "__main__":
    run()
