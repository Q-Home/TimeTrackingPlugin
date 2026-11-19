"""Q-Home identity migration and release feeds, using temporary files only."""
from copy import deepcopy
import importlib.util
import configparser
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/(name+'.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


migration = module('migrate_qhome')
release = module('release_feed')


class IdentityMigrationTests(unittest.TestCase):
    def database(self):
        record = dict(name='timetrackingplugin', folder='timetrackingplugin',
                      author_name='Legacy Team', author_email='legacy@example.invalid',
                      version='1.3.3', autoupdate=1, directories={'config':'unchanged'},
                      epoch_firstinstalled=123, custom={'keep':True})
        key = migration.identity(record); record['md5'] = key
        return {'plugins':{key:record, 'unrelated':{'name':'other','private':'preserved'}}, 'schema':2}

    def test_migration_renames_identity_and_preserves_installation(self):
        original = self.database(); result = migration.converted(original)
        self.assertEqual(len(result['plugins']),2)
        record = next(r for r in result['plugins'].values() if r.get('name')=='timetrackingplugin')
        self.assertEqual(record['author_name'],'Q-Home')
        self.assertEqual(record['author_email'],'info@q-home.be')
        self.assertEqual(record['md5'],migration.identity(record))
        self.assertEqual(record['autoupdate'],3)
        self.assertEqual(record['releasecfg'],migration.FEED)
        self.assertEqual(record['version'],'1.3.3')
        self.assertEqual(record['directories'],{'config':'unchanged'})
        self.assertEqual(record['custom'],{'keep':True})
        self.assertEqual(result['plugins']['unrelated'],original['plugins']['unrelated'])
        self.assertNotEqual(result,original)
        self.assertEqual(migration.converted(result),result)

    def test_inconsistent_or_duplicate_installation_is_rejected(self):
        db = self.database(); key = next(iter(db['plugins']))
        db['plugins'][key]['md5']='incorrect'
        with self.assertRaises(ValueError): migration.converted(db)
        db = self.database(); db['plugins']['duplicate']=deepcopy(next(iter(db['plugins'].values())))
        with self.assertRaises(ValueError): migration.converted(db)

    def test_existing_target_identity_is_not_overwritten(self):
        db=self.database(); converted=migration.converted(db)
        new_key=next(k for k in converted['plugins'] if k!='unrelated')
        db['plugins'][new_key]={'name':'conflict'}
        with self.assertRaises(ValueError): migration.converted(db)

    def test_atomic_database_shadow_and_private_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); path=home/'data/system/plugindatabase.json'
            path.parent.mkdir(parents=True); original=json.dumps(self.database()).encode()
            path.write_bytes(original)
            migration.migrate(home)
            self.assertEqual(path.read_bytes(),path.with_name(path.name+'-').read_bytes())
            self.assertEqual(json.loads(path.read_bytes()),migration.converted(self.database()))
            saved=list((home/'data/plugins/timetrackingplugin/identity-backups').glob('*.json'))
            self.assertEqual(len(saved),1); self.assertEqual(saved[0].read_bytes(),original)

    def test_write_failure_restores_both_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); path=home/'data/system/plugindatabase.json'
            path.parent.mkdir(parents=True); original=json.dumps(self.database()).encode()
            path.write_bytes(original); shadow=path.with_name(path.name+'-'); shadow.write_bytes(b'old shadow')
            real=migration.atomic_bytes; calls=[]
            def fail_once(target, content, reference):
                calls.append(target)
                if len(calls)==2: raise OSError('simulated failure')
                return real(target,content,reference)
            with patch.object(migration,'atomic_bytes',side_effect=fail_once):
                with self.assertRaises(OSError): migration.migrate(home)
            self.assertEqual(path.read_bytes(),original); self.assertEqual(shadow.read_bytes(),b'old shadow')


class ReleaseFeedTests(unittest.TestCase):
    def number(self):
        config=configparser.ConfigParser();config.read(ROOT/'plugin.cfg',encoding='utf-8')
        return config['PLUGIN']['VERSION']
    def event(self):
        return {'repository':{'full_name':release.REPO},'release':{
            'tag_name':'v'+self.number(),'draft':False,'prerelease':False,'published_at':'2026-11-19T00:00Z'}}

    def test_published_release_uses_exact_tag_archive(self):
        text=release.feed(self.event(),ROOT)
        self.assertIn('VERSION='+self.number()+'\n',text)
        self.assertIn('/archive/refs/tags/v'+self.number()+'.zip',text)
        self.assertNotIn('/main.zip',text)

    def test_drafts_prereleases_wrong_version_and_repository_rejected(self):
        for key,value in [('draft',True),('prerelease',True),('published_at',None),('tag_name','v999.0.0'),('tag_name','v'+self.number()+'-rc1')]:
            event=self.event(); event['release'][key]=value
            with self.assertRaises(ValueError): release.feed(event,ROOT)
        event=self.event(); event['repository']['full_name']='other/repository'
        with self.assertRaises(ValueError): release.feed(event,ROOT)

    def test_feed_never_rolls_back_to_older_release(self):
        text=release.feed(self.event(),ROOT)
        with self.assertRaises(ValueError): release.prevent_downgrade(text,'[AUTOUPDATE]\nVERSION=999.0.0\n')
        release.prevent_downgrade(text,'[AUTOUPDATE]\nVERSION=0.0.0\n')
        release.prevent_downgrade(text,text)


if __name__=='__main__': unittest.main()
