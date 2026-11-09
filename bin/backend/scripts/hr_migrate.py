#!/usr/bin/env python3
"""Explicit, idempotent identity migration. Preview is the default; never at startup."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pymongo import MongoClient
from app.hr.service import HRService, identifier


def preview(service):
    state=service.state();links={};unresolved=[]
    for event in service.db.badge_logs.find({}):
        key=service.identity_key(event);uid=service.resolve(event,state)
        if uid.startswith('unresolved:'):
            if key not in unresolved:unresolved.append(key)
        elif not event.get('employee_id'):links[key]=uid
    return {'revision':state['revision'],'resolved_links':links,'unresolved':unresolved}


def migrate(service,apply=False):
    report=preview(service)
    if not apply:return report
    for identity,uid in report['resolved_links'].items():
        state=service.state()
        if state['identity_links'].get(identity)==uid:continue
        service.setting('identity',{'revision':state['revision'],'identity_key':identity,
            'employee_id':uid,'reason':'Expliciete migratie van historische identiteiten'},'migration:operator',identifier())
    # Only relationship metadata changes; original username/timestamp/action stay intact.
    updated=0
    for event in service.db.badge_logs.find({'employee_id':{'$in':[None,'']}}):
        uid=service.resolve(event)
        if not uid.startswith('unresolved:'):
            updated+=service.db.badge_logs.update_one({'_id':event['_id'],'employee_id':{'$in':[None,'']}},
                {'$set':{'employee_id':uid,'identity_migration':'hr-v1'}}).modified_count
    return {**report,'metadata_documents_updated':updated}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Apply only after an independent backup and test restore')
    args=parser.parse_args()
    db=MongoClient(os.environ.get('MONGO_URI','mongodb://localhost:27017/timetracking')).get_default_database()
    print(json.dumps(migrate(HRService(db),args.apply),indent=2))
