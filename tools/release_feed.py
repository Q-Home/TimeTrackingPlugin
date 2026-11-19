"""Validate a published stable release before generating the LoxBerry feed."""
import argparse
import configparser
import json
from pathlib import Path
import re

REPO = 'Q-Home/TimeTrackingPlugin'


def version(value):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value):
        raise ValueError('Stable versions must use MAJOR.MINOR.PATCH.')
    return tuple(map(int, value.split('.')))


def feed(event, source):
    release = event['release']
    if event['repository']['full_name'] != REPO or release['draft'] or release['prerelease'] or not release.get('published_at'):
        raise ValueError('Only published stable releases from the Q-Home repository are accepted.')
    tag = release['tag_name']
    number = tag[1:] if tag.startswith('v') else tag
    version(number)
    config = configparser.ConfigParser()
    config.read(Path(source)/'plugin.cfg', encoding='utf-8')
    if config['PLUGIN']['VERSION'] != number or config['AUTHOR']['NAME'] != 'Q-Home' or config['AUTHOR']['EMAIL'] != 'info@q-home.be':
        raise ValueError('Release tag, plugin version and Q-Home identity must agree.')
    return f'[AUTOUPDATE]\nVERSION={number}\nARCHIVEURL=https://github.com/{REPO}/archive/refs/tags/{tag}.zip\nINFOURL=https://github.com/{REPO}/releases/tag/{tag}\n'


def prevent_downgrade(new, previous):
    def parse(text):
        config = configparser.ConfigParser(); config.read_string(text)
        return version(config['AUTOUPDATE']['VERSION'])
    if parse(new) < parse(previous):
        raise ValueError('Refusing to replace the feed with an older release.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--previous')
    args = parser.parse_args()
    text = feed(json.loads(Path(args.event).read_text(encoding='utf-8')), args.source)
    if args.previous and Path(args.previous).exists():
        prevent_downgrade(text, Path(args.previous).read_text(encoding='utf-8'))
    Path(args.output).write_text(text, encoding='utf-8')
