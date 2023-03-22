import dataset

from tr_rm import config

context = {}


def conn():
    if not context.get("db"):
        context["db"] = dataset.connect(config.DATABASE_URL, sqlite_wal_mode=False)
    return context["db"]


def table(table: str):
    return conn()[table]


def types():
    return conn().types


def query(query: str, *args, **kwargs):
    return conn().query(query, *args, **kwargs)
