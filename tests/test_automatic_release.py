"""Release transactions against a fake GitHub API; never publish externally."""
import base64
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from automatic_release import publish, marker, replace_version
from release_feed import feed

SOURCE='a'*40
OLD='b'*40
BUMP='c'*40
TEXT='[AUTHOR]\nNAME=Q-Home\nEMAIL=info@q-home.be\n[PLUGIN]\nVERSION=1.3.8\nNAME=timetrackingplugin\n'


class FakeGitHub:
    def __init__(self):
        self.head=SOURCE;self.tags={};self.releases={};self.writes=[];self.text=TEXT
        self.commits={SOURCE:{'tree':{'sha':'source-tree'},'parents':[],'message':'Tested main'}}
        self.fail_release=False;self.reject_main=False
    def request(self,method,path,data=None,missing=False):
        if method!='GET':self.writes.append((method,path,deepcopy(data)))
        if method=='GET':
            if path=='git/ref/heads/main':return {'object':{'sha':self.head}}
            if path.startswith('git/ref/tags/'):
                sha=self.tags.get(path.removeprefix('git/ref/tags/'))
                return {'object':{'type':'commit','sha':sha}} if sha else None
            if path=='releases?per_page=100':return list(self.releases.values())
            if path.startswith('releases/tags/'):return self.releases.get(path.removeprefix('releases/tags/'))
            if path.startswith('git/commits/'):return self.commits[path.removeprefix('git/commits/')]
            if path.startswith('contents/plugin.cfg?ref='):return {'content':base64.b64encode(self.text.encode()).decode()}
            if path.startswith('compare/'):return {'files':[{'filename':'plugin.cfg'}]}
        if path=='git/trees':self.text=data['tree'][0]['content'];return {'sha':'version-tree'}
        if path=='git/commits':
            self.commits[BUMP]={'message':data['message'],'parents':[{'sha':p} for p in data['parents']],'tree':{'sha':data['tree']}}
            return {'sha':BUMP}
        if path=='git/refs/heads/main':
            if self.reject_main:raise RuntimeError('Main advanced; fast-forward rejected')
            assert data['force'] is False
            self.head=data['sha'];return {}
        if path=='git/refs':
            tag=data['ref'].removeprefix('refs/tags/')
            assert tag not in self.tags
            self.tags[tag]=data['sha'];return {}
        if path=='releases':
            if self.fail_release:raise RuntimeError('Temporary release failure')
            self.releases[data['tag_name']]={**data,'published_at':'2026-11-20T00:00:00Z'}
            return self.releases[data['tag_name']]
        raise AssertionError((method,path,data))
    def previous(self):
        self.tags['v1.3.8']=OLD
        self.releases['v1.3.8']={'tag_name':'v1.3.8','draft':False,'prerelease':False,'published_at':'2026-11-19T00:00Z'}


class AutomaticReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name);self.path=self.source/'plugin.cfg';self.path.write_text(TEXT,encoding='utf-8')
        self.api=FakeGitHub()
    def run_release(self):return publish(self.api,SOURCE,self.source)
    def test_first_merge_publishes_exact_tested_commit_and_valid_feed(self):
        event=self.run_release()
        self.assertEqual(event['release']['tag_name'],'v1.3.8')
        self.assertEqual(self.api.tags['v1.3.8'],SOURCE)
        self.assertIn('/v1.3.8.zip',feed(event,self.source))
        self.assertFalse(any(path=='git/refs/heads/main' for _,path,_ in self.api.writes))
    def test_same_run_is_idempotent_and_can_repair_its_feed(self):
        first=self.run_release();count=len(self.api.writes)
        self.assertEqual(self.run_release(),first)
        self.assertEqual(len(self.api.writes),count)
    def test_new_merge_without_version_bump_gets_next_patch(self):
        self.api.previous();event=self.run_release()
        self.assertEqual(event['release']['tag_name'],'v1.3.9')
        self.assertEqual(self.api.tags['v1.3.8'],OLD)
        self.assertEqual(self.api.tags['v1.3.9'],BUMP)
        self.assertEqual(self.api.head,BUMP)
        self.assertEqual(self.path.read_text(),replace_version(TEXT,'1.3.9'))
        self.assertIn('/v1.3.9.zip',feed(event,self.source))
    def test_explicit_new_version_does_not_get_bumped_again(self):
        self.api.previous();self.path.write_text(replace_version(TEXT,'1.4.0'),encoding='utf-8')
        self.assertEqual(self.run_release()['release']['tag_name'],'v1.4.0')
        self.assertEqual(self.api.head,SOURCE)
    def test_unrelated_new_main_commit_skips_obsolete_test_run(self):
        self.api.head=OLD;self.api.commits[OLD]={'parents':[],'message':'Newer merge'}
        self.assertIsNone(self.run_release());self.assertEqual(self.api.writes,[])
    def test_failed_release_resumes_version_only_commit_without_second_bump(self):
        self.api.previous();self.api.fail_release=True
        with self.assertRaises(RuntimeError):self.run_release()
        self.assertEqual(self.api.head,BUMP);self.assertEqual(self.api.tags['v1.3.9'],BUMP)
        self.api.fail_release=False;self.path.write_text(TEXT,encoding='utf-8')
        self.assertEqual(self.run_release()['release']['tag_name'],'v1.3.9')
        self.assertEqual(sum(path=='git/commits' for _,path,_ in self.api.writes),1)
    def test_main_race_does_not_publish_or_force_overwrite(self):
        self.api.previous();self.api.reject_main=True
        with self.assertRaises(RuntimeError):self.run_release()
        self.assertNotIn('v1.3.9',self.api.tags)
        self.assertNotIn('v1.3.9',self.api.releases)
    def test_tag_collision_is_skipped_without_moving_old_tags(self):
        self.api.previous();self.api.tags['v1.3.9']=OLD
        self.assertEqual(self.run_release()['release']['tag_name'],'v1.3.10')
        self.assertEqual(self.api.tags['v1.3.9'],OLD)
    def test_deleted_published_tag_is_not_recreated_for_different_code(self):
        self.api.previous();del self.api.tags['v1.3.8']
        self.assertEqual(self.run_release()['release']['tag_name'],'v1.3.9')
        self.assertNotIn('v1.3.8',self.api.tags)
    def test_existing_draft_is_not_published_by_accident(self):
        self.api.tags['v1.3.8']=SOURCE
        self.api.releases['v1.3.8']={'tag_name':'v1.3.8','draft':True,'prerelease':False,'published_at':None}
        with self.assertRaises(ValueError):self.run_release()
        self.assertEqual(self.api.writes,[])
    def test_resume_rejects_changes_beyond_version_metadata(self):
        self.api.head=BUMP;self.api.text=replace_version(TEXT,'1.3.9')+'OTHER=modified\n'
        self.api.commits[BUMP]={'parents':[{'sha':SOURCE}],'message':marker('1.3.9',SOURCE)}
        self.assertIsNone(self.run_release());self.assertEqual(self.api.writes,[])


if __name__=='__main__':unittest.main()
