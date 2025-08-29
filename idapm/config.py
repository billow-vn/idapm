#!/usr/bin/env python3
# coding: UTF-8

import json
from pathlib import Path
from os.path import expanduser


class Config(object):

    def __init__(self):
        home_dir = expanduser("~")
        self.config_path = Path(home_dir).joinpath('idapm.json')

    def check_duplicate(self, plugin_repo):
        with open(str(self.config_path.absolute()), 'r+') as f:
            config_json = json.load(f)
            if plugin_repo not in config_json['plugins']:
                return False

            return True

    def check_exists(self):
        return self.config_path.exists(follow_symlinks=True)

    def make_config(self, version: str | int | None = 700) -> None:
        config_json = {'plugins': [], 'version': int(version or 700)}
        with open(str(self.config_path.absolute()), 'w') as f:
            json.dump(config_json, f, indent=2)

    def add_plugin(self, plugin_repo):
        with open(str(self.config_path.absolute()), 'r+') as f:
            config_json = json.load(f)
            if plugin_repo not in config_json['plugins']:
                config_json['plugins'].append(plugin_repo)
                f.seek(0)
                json.dump(config_json, f, indent=2)
                return True

            else:
                return False

    def update_version(self, version: str | int | None = 700):
        version = int(version or 700)
        with open(str(self.config_path.absolute()), 'r+') as f:
            config_json = json.load(f)
            config_json['version'] = version if version > 700 else 700
            f.seek(0)
            json.dump(config_json, f, indent=2)
            return True

    def get_version(self):
        with open(str(self.config_path.absolute()), 'r+') as f:
            config_json = json.load(f)

            version = None
            if 'version' in config_json:
                version = config_json['version']

            return int(version or 700)

    def list_plugins(self):
        with open(str(self.config_path.absolute()), 'r+') as f:
            config_json = json.load(f)
            no_duplicate_plugins = list(set(config_json['plugins']))
            config_json['plugins'] = no_duplicate_plugins
            f.seek(0)
            json.dump(config_json, f, indent=2)
            return no_duplicate_plugins
