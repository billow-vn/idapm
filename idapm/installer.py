#!/usr/bin/env python3
# coding: UTF-8

import glob
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
import re

from . import config
from colorama import Fore
from os.path import expanduser


def parse_repo(repo: str) -> tuple[str, str]:
    """
    return (repo_name, repo_url)

    Example for repo format:
      - 'user/repo'
      - 'repo'
      - 'https://github.com/user/repo(.git)'
      - 'git@github.com:user/repo(.git)'
    """

    m = re.match(r"(?:https://[^/]+/|git@[^:]+:)([^/]+/[^/]+?)(?:\.git)?$", repo)
    if m:
        repo_name = m.group(1)
        repo_url = repo
        return repo_name, repo_url

    if "/" in repo:
        repo_name = repo
    else:
        repo_name = f"{repo}/{repo}"

    repo_url = f"https://github.com/{repo_name}.git"
    return repo_name, repo_url


def get_ida_version(c: config.Config | None = None) -> int | None:
    c = c or config.Config()

    return c.get_version()


def find_ida_home() -> str | Path | None:
    platform_name = platform.system()
    ida_paths = []
    if platform_name == 'Darwin':
        ida_paths.extend(glob.glob(r'/Applications/IDA*/Contents/MacOS'))
    elif platform_name == 'Windows':
        ida_paths.extend(glob.glob(r'C:\Program Files*\IDA*'))
    elif platform_name == 'Linux':
        home_dir = expanduser('~')
        ida_paths.extend(glob.glob(os.path.join(home_dir, 'ida*')))

    ida_paths = [i for i in ida_paths if not i.endswith('idapm.json')]

    return ida_paths[0] if ida_paths[0] else None


def find_ida_home_base(ida_home: str | Path | None = None) -> Path | str | None:
    ida_home = Path(ida_home) if ida_home else find_ida_home()
    platform_name = platform.system()
    if platform_name == 'Darwin' and ida_home:
        ida_home = str(ida_home.absolute()).replace('/Contents/MacOS/plugins', '')
        ida_home = Path(ida_home)

    return ida_home


def get_plugin_dir(c: config.Config | None = None) -> Path | None:
    c = c or config.Config()

    platform_name = platform.system()
    ida_home = find_ida_home()
    ida_home = Path(ida_home) if ida_home else None

    ida_home_base = find_ida_home_base(ida_home)
    ida_home_base = Path(ida_home_base) if ida_home_base else None
    ida_version = get_ida_version(c)

    if ida_version <= 700:
        if platform_name == 'Darwin':
            return Path(ida_home_base, 'ida.app/Contents/MacOS/plugins')
        elif platform_name == 'Windows':
            return Path(ida_home, 'plugins')
        elif platform_name == 'Linux':
            return Path(ida_home, 'plugins')
    else:
        home_dir = expanduser('~')
        if platform_name == 'Windows':
            return Path(os.getenv('APPDATA'), 'Hex-Rays/IDA Pro/plugins')
        else:
            return Path(home_dir, '.idapro/plugins')

    return None


def install_from_local(dir_name, c: config.Config | None = None, symlinks: bool | None = False) -> bool:
    c = c or config.Config()

    ida_plugins_dir = get_plugin_dir(c)
    if ida_plugins_dir is None:
        print(Fore.RED + 'Your OS is unsupported...')
        return False

    dir_path = Path(dir_name)
    for file_target_path in dir_path.glob('**/*.py', recurse_symlinks=True):
        file_rel_path = file_target_path.relative_to(dir_path)

        if file_rel_path.parents[0] == ".":
            dst = ida_plugins_dir.joinpath(
                file_rel_path
            )

            src = file_target_path
        else:
            folder_name = file_rel_path.parts[0]
            dst = ida_plugins_dir.joinpath(folder_name)
            if dst.exists():
                continue

            src = dir_path.joinpath(folder_name)

        try:
            if not symlinks:
                shutil.copyfile(src, dst)
                print('Copy to {0} from {1}'.format(src, dst))
            else:
                os.symlink(src, dst)
                print('Symlink to {0} from {1}'.format(src, dst))
        except FileExistsError:
            print('File {0} already exists'.format(dst))

    print(Fore.CYAN + 'Installed successfully!')
    return True


def install_from_github(repo: str, c: config.Config | None = None):
    '''
    After git clone plugin in ida_plugins_dir/idapm, and create a symbolic link to the python file from ida_plugins_dir
    Only links *.py files in root and the first parent directory containing *.py files.
    '''
    c = c or config.Config()
    (repo_name, repo_url) = parse_repo(repo)

    print('Try: git clone {0}'.format(repo_url))

    ida_plugins_dir = get_plugin_dir(c)
    idapm_path = ida_plugins_dir.parent.joinpath('idapm')
    if ida_plugins_dir.exists():
        repo_name = shlex.quote(repo_name)  # Countermeasures for command injection
        installed_path = idapm_path.joinpath(repo_name).absolute()
        if not installed_path.exists():
            proc = subprocess.Popen(
                [
                    r'git', r'clone',
                    repo_url,
                    str(installed_path)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            outs, errs = proc.communicate()
            if (outs is not None) and (len(outs) != 0):
                msg = outs.decode('ascii').replace('\n', '')
                print(msg)

            if (errs is not None) and (len(errs) != 0):
                msg = errs.decode('ascii').replace('\n', '')
                print(msg)
                if ('Repository not found' in msg) or ('already exists and is not an empty directory' in msg):
                    return False

        install_from_local(installed_path, c, symlinks=True)
        return True

    else:
        print(Fore.RED + 'Your OS is unsupported...')
        return False


def list_plugins(c: config.Config | None = None) -> tuple[list[str], list[str]] | None:
    c = c or config.Config()

    platform_name = platform.system()
    ida_plugins_dir = get_plugin_dir(c)

    exclude_files = {
        'plugins.cfg',
        'bochs',
        'idapm',
        'platformthemes',
        'hexrays_sdk',
    }

    if platform_name == 'Darwin':
        plugin_added = set(os.listdir(ida_plugins_dir)) - exclude_files
        plugin_added = [i for i in plugin_added if (not i.endswith('.dylib')) and (not i.endswith('.h'))]
    elif platform_name == 'Windows':
        plugin_added = set(os.listdir(ida_plugins_dir)) - exclude_files
        plugin_added = [i for i in plugin_added if not i.endswith('.dll')]
    elif platform_name == 'Linux':
        plugin_added = set(os.listdir(ida_plugins_dir)) - exclude_files
        plugin_added = [i for i in plugin_added if not i.endswith('.so')]
    else:
        print('Your OS is unsupported...')
        return None

    print(Fore.CYAN + 'List of scripts in IDA plugin directory:')
    for plugin in plugin_added or []:
        print(' - %s' % plugin)

    print(Fore.CYAN + '\nList of plugins in config:')
    plugin_repos = c.list_plugins()
    for plugin in plugin_repos or []:
        print(' - %s' % plugin)

    return plugin_repos, plugin_added
