import os
import toml

from pathlib import Path


# TODO: use types.SimpleNamespace inheritance
class Configurator:
    """Loads a dict of config from default config or env var override and behaves like an object, ie config.VALUE"""
    configuration = {}

    def __init__(self, filepath=None):
        p = Path(filepath) if filepath else Path(__file__).parent / "../config.toml"
        self.filepath = p.resolve()

        if not self.configuration:
            self.configure()

    def configure(self):
        with self.filepath.open() as f:
            data = toml.load(f)
        for k, v in data.items():
            if override := os.getenv(k):
                if k in data["_FLOAT_VARS"]:
                    override = float(override)
                elif k in data["_INT_VARS"]:
                    override = int(override)
                self.configuration[k] = override
            else:
                self.configuration[k] = v
        self.check()

    def override(self, **kwargs):
        self.configuration.update(kwargs)
        self.check()

    def check(self):
        """Sanity check on config"""
        # https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
        if self.configuration.get("DATABASE_URL", "").startswith("postgres://"):
            self.configuration["DATABASE_URL"] = self.configuration["DATABASE_URL"].\
                replace("postgres://", "postgresql://")

    def __getattr__(self, __name):
        return self.configuration.get(__name)

    @property
    def __dict__(self):
        return self.configuration


config = Configurator()
