"""Publish tested main commits, with idempotent patch numbering and safe retries."""
import argparse
import base64
import configparser
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from release_feed import REPO, version


class GitHub:
    def request(self, method, path, data=None, missing=False):
        token=os.environ['GH_TOKEN']
        request=Request('https://api.github.com/repos/'+REPO+'/'+path,
            data=None if data is None else json.dumps(data).encode(),method=method,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                     'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28',
                     'User-Agent':'Q-Home-TimeTracking-release'})
        try:
            with urlopen(request,timeout=30) as response:return json.load(response)
        except HTTPError as exc:
            if missing and exc.code==404:return None
            raise RuntimeError('GitHub release operation failed (HTTP '+str(exc.code)+').') from None


def config_version(text):
    config=configparser.ConfigParser();config.read_string(text)
    number=config['PLUGIN']['VERSION'];version(number)
    if config['AUTHOR']['NAME']!='Q-Home' or config['AUTHOR']['EMAIL']!='info@q-home.be':
        raise ValueError('Only the Q-Home plugin identity may be released.')
    return number


def replace_version(text, number):
    version(number)
    # plugin.cfg has one VERSION entry. Keep comments and all other bytes intact.
    result,count=re.subn(r'(?m)^VERSION=[^\r\n]+', 'VERSION='+number,text)
    if count!=1:raise ValueError('Expected one plugin VERSION entry.')
    return result


def tag_commit(api, tag):
    ref=api.request('GET','git/ref/tags/'+tag,missing=True)
    if ref is None:return None
    obj=ref['object']
    for _ in range(5):
        if obj['type']=='commit':return obj['sha']
        if obj['type']!='tag':break
        obj=api.request('GET','git/tags/'+obj['sha'])['object']
    raise ValueError('Release tag does not resolve to a commit.')


def marker(number, sha):
    return 'Q-Home release '+number+' [skip ci]\n\nQTIME_SOURCE='+sha


def publish(api, tested_sha, source):
    if not re.fullmatch(r'[0-9a-f]{40}',tested_sha):raise ValueError('A tested commit SHA is required.')
    path=Path(source)/'plugin.cfg';original=path.read_text(encoding='utf-8')
    number=config_version(original);candidate=tested_sha
    head=api.request('GET','git/ref/heads/main')['object']['sha']
    if head!=tested_sha:
        # Resume only our exact version-only child commit after a partial failure.
        commit=api.request('GET','git/commits/'+head)
        if [p['sha'] for p in commit['parents']]!=[tested_sha]:return None
        current=api.request('GET','contents/plugin.cfg?ref='+head)
        text=base64.b64decode(current['content']).decode('utf-8');resumed=config_version(text)
        if commit['message']!=marker(resumed,tested_sha) or text!=replace_version(original,resumed):return None
        comparison=api.request('GET','compare/'+tested_sha+'...'+head)
        if [f['filename'] for f in comparison['files']]!=['plugin.cfg']:return None
        number=resumed;candidate=head;path.write_text(text,encoding='utf-8')

    existing=tag_commit(api,'v'+number)
    releases=api.request('GET','releases?per_page=100')
    stable=[]
    for release in releases:
        if release['draft'] or release['prerelease']:continue
        try:stable.append(version(release['tag_name'].removeprefix('v')))
        except ValueError:continue
    latest=max(stable,default=(0,0,0))
    used_number=any(not r['draft'] and not r['prerelease'] and r['tag_name'].removeprefix('v')==number for r in releases)
    if existing not in (None,candidate) or version(number)<latest or (existing is None and used_number):
        if candidate!=tested_sha:raise ValueError('Resumed version collides with an existing release; inspect tags.')
        major,minor,patch=max(version(number),latest)
        number=f'{major}.{minor}.{patch+1}'
        # Never overwrite an existing stable or prerelease tag.
        while tag_commit(api,'v'+number) is not None:
            patch+=1;number=f'{major}.{minor}.{patch+1}'
        text=replace_version(original,number)
        base=api.request('GET','git/commits/'+tested_sha)
        tree=api.request('POST','git/trees',{'base_tree':base['tree']['sha'],
            'tree':[{'path':'plugin.cfg','mode':'100644','type':'blob','content':text}]})
        commit=api.request('POST','git/commits',{'message':marker(number,tested_sha),
            'tree':tree['sha'],'parents':[tested_sha],
            'author':{'name':'Q-Home','email':'info@q-home.be'}})
        candidate=commit['sha']
        # Non-force fast-forward fails safely if a new merge arrived meanwhile.
        api.request('PATCH','git/refs/heads/main',{'sha':candidate,'force':False})
        path.write_text(text,encoding='utf-8');existing=None

    tag='v'+number
    if existing is None:
        api.request('POST','git/refs',{'ref':'refs/tags/'+tag,'sha':candidate})
    elif existing!=candidate:raise ValueError('Refusing to move an existing release tag.')
    release=api.request('GET','releases/tags/'+tag,missing=True)
    if release is None:
        release=api.request('POST','releases',{'tag_name':tag,'target_commitish':candidate,
            'name':'TimeTrackingPlugin '+number,'draft':False,'prerelease':False,
            'body':'Q-Home TimeTrackingPlugin '+number+'.\n\nAutomatisch gepubliceerd na geslaagde controles op main. De LoxBerry-updateverwijzing wordt in dezelfde taak bijgewerkt.'})
    if release['draft'] or release['prerelease'] or not release.get('published_at'):
        raise ValueError('An existing draft or prerelease is not published automatically.')
    if tag_commit(api,tag)!=candidate:raise ValueError('Published tag does not match the tested release source.')
    return {'repository':{'full_name':REPO},'release':release}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--sha',required=True);parser.add_argument('--source',default='.')
    parser.add_argument('--event-output',required=True)
    args=parser.parse_args()
    if os.environ.get('GITHUB_REPOSITORY')!=REPO:raise ValueError('Unexpected repository.')
    event=publish(GitHub(),args.sha,args.source)
    if event:
        Path(args.event_output).write_text(json.dumps(event),encoding='utf-8')
        print('Published or verified '+event['release']['tag_name'])
    else:print('A newer main commit supersedes this run; its own successful checks will publish it.')
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:
        output.write('publish='+('true' if event else 'false')+'\n')
