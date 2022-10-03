from ruamel.yaml import YAML

_configuration = None

def get_configuration():
    if _configuration is None:
        raise Exception('core-tools configuration not loaded')
    return _configuration

def load_configuration(filename):
    global _configuration

    _configuration = Configuration(filename)
    return _configuration

class Configuration:
    def __init__(self, filename):
        self.filename = filename
        yaml = YAML()
        with open(filename) as fp:
            self._config = yaml.load(fp)

    def get(self, name, default=None):
        try:
            return self._get(name)
        except KeyError:
            return default

    def _get(self, name):
        try:
            parts = name.split('.')
            value = self._config
            for part in parts:
                if value is None:
                    raise KeyError()
                value = value[part]
        except KeyError:
            raise KeyError(name) from None
        return value

    def __getitem__(self, name):
        return self._get(name)
