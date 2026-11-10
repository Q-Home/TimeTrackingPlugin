"""Provision registration identities only from the authenticated Loxone ingress."""
from datetime import datetime, timezone
import hashlib
from pymongo.errors import DuplicateKeyError
from app.hr.service import HRError
from app.utils.external_identity import external_id_values


class EmployeeProvisioning:
    def __init__(self,db,hr):self.db,self.hr=db,hr

    @staticmethod
    def normalize(data):
        value=dict(data)
        ids=[]
        for key in ('user_id','userid','userId'):
            raw=value.get(key)
            if raw in (None,''):continue
            if isinstance(raw,bool) or not isinstance(raw,(str,int)):raise ValueError('Ongeldige Loxone-userid.')
            text=str(raw).strip()
            if len(text)>128 or any(ord(c)<32 for c in text):raise ValueError('Ongeldige Loxone-userid.')
            if text:ids.append(text)
        if len(set(ids))>1:raise ValueError('De opgegeven Loxone-userids spreken elkaar tegen.')
        value['user_id']=ids[0] if ids else ''
        for key,limit in [('username',120),('first_name',120),('last_name',120)]:
            raw=value.get(key) or ''
            if not isinstance(raw,str) or len(raw)>limit or any(ord(c)<32 for c in raw):raise ValueError('Ongeldige medewerkergegevens.')
            value[key]=raw.strip()
        return value

    @staticmethod
    def result(user=None,status='unidentified',key=None):
        identity=('external:'+key[3:]) if key and key.startswith('id:') else ('username:'+key[5:]) if key and key.startswith('name:') else None
        return {'user':user,'status':status,'identity_key':identity}

    def ensure(self,data):
        external=data['user_id'];name=data['username']
        if not external and not name:return self.result()
        key='id:'+external if external else 'name:'+name
        digest=hashlib.sha256(key.encode()).hexdigest()
        for attempt in range(4):
            current=self.db.users.find_one({'provisioning_key':key})
            if current:return self.result(current,'existing',key)
            matches=list(self.db.users.find({'user_id':{'$in':external_id_values(external)}})) if external else []
            if len(matches)>1:return self.result(status='identity_conflict',key=key)
            named=self.db.users.find_one({'username':name}) if name else None
            provisional=self.db.users.find_one({'provisioning_key':'name:'+name}) if name else None
            if not matches and named and provisional and named['_id']!=provisional['_id']:
                return self.result(status='identity_conflict',key=key)
            candidate=matches[0] if matches else provisional or named
            if candidate:
                if candidate.get('archived') and matches:return self.result(candidate,'archived',key)
                if candidate.get('archived') and not external:return self.result(status='identity_conflict',key=key)
                old_external=str(candidate.get('user_id') or '')
                old_key=candidate.get('provisioning_key')
                # Never claim a different identity by a reused name, or bind a
                # privileged login merely because a new badge used that name.
                explicit=bool(matches)
                compatible=not candidate.get('archived') and (not old_external or old_external==external or not external) and (
                    not old_key or old_key==key or (external and old_key=='name:'+name))
                if compatible and (explicit or candidate.get('role','user')=='user'):
                    try:
                        if external and not old_external:
                            state=self.hr.state();identity='external:'+external
                            linked=state['identity_links'].get(identity)
                            if linked and linked!=str(candidate['_id']):return self.result(status='identity_conflict',key=key)
                            if not linked:
                                # Commit identity resolution through HR's revision
                                # guard before it can affect approved calculations.
                                self.hr.setting('identity',{'revision':state['revision'],'identity_key':identity,
                                    'employee_id':str(candidate['_id']),'reason':'Automatische koppeling bij eerste vertrouwde Loxone-registratie'},
                                    'system:loxone-provisioning','provision-'+digest[:32])
                        query={'_id':candidate['_id']}
                        query['provisioning_key']=old_key if old_key is not None else {'$exists':False}
                        # Do not downgrade a stable userid identity to a name-only
                        # key when a legacy reader sends no userid on a later scan.
                        values={'provisioning_key':old_key if not external and old_key else key}
                        if external and not old_external:values['user_id']=external
                        result=self.db.users.update_one(query,{'$set':values})
                        if not result.matched_count:continue
                        return self.result(self.db.users.find_one({'_id':candidate['_id']}),'linked',key)
                    except DuplicateKeyError:continue
                    except HRError:return self.result(status='identity_conflict',key=key)
            # A name can be missing, archived, reused or held as a historical
            # alias. In those cases use a stable internal name; never merge.
            alias=self.hr.state()['identity_links'].get('username:'+name)
            preferred=name if len(name)>=3 and candidate is None and not alias and attempt==0 else 'loxone-'+digest[:24]
            user={'username':preferred,'email':'loxone-'+digest+'@users.invalid',
                'first_name':data['first_name'] or name or 'Loxone medewerker',
                'last_name':data['last_name'],'user_id':external,'loxone_username':name,
                'provisioning_key':key,'provisioned_by':'loxone','email_is_placeholder':True,
                'role':'user','blocked':False,'password':None,
                'created_at':datetime.now(timezone.utc),'updated_at':datetime.now(timezone.utc)}
            try:
                result=self.db.users.insert_one(user);user['_id']=result.inserted_id
                return self.result(user,'created',key)
            except DuplicateKeyError:continue
        return self.result(status='identity_conflict',key=key)
