import json
import socket


class SyncError(Exception):
    def __init__(self, code): self.code = code


MESSAGES = {
    'bridge_unavailable':'De LoxBerry-hostadapter is niet bereikbaar. Controleer de service en de backend-socketmount.',
    'configuration':'Miniserverconfiguratie of ondersteunde LoxBerry-bibliotheek ontbreekt.',
    'tls':'Kies HTTPS in LoxBerry en gebruik een hostnaam met een vertrouwd certificaat.',
    'authentication':'Aanmelden bij de Miniserver mislukt. Controleer het LoxBerry-Miniserveraccount.',
    'permissions':'Het LoxBerry-account heeft onvoldoende gebruikersbeheerrechten op de Miniserver.',
    'network':'De Miniserver is niet bereikbaar of antwoordt niet binnen de tijdslimiet.',
    'unsupported':'Deze firmware wordt niet ondersteund. Deze adapter vereist Miniserver 17.x en LoxBerry 3.x/4.x met mshttp_call2.',
    'identity_changed':'De Miniserveridentiteit is gewijzigd. Controleer de selectie en koppel bewust opnieuw.',
    'user_missing':'De gekoppelde UUID bestaat niet meer. Er wordt niet automatisch aan een naamgenoot gekoppeld.',
    'response':'De Miniserver gaf geen bevestigde, geldige succesrespons.',
    'verification':'De teruggelezen custom fields komen niet overeen. Controleer de gebruiker voordat je opnieuw probeert.',
    'invalid':'Ongeldige of niet-toegestane adapteraanvraag.',
    'busy':'Er wordt al gesynchroniseerd of ingesteld. Probeer later opnieuw.',
}


class Bridge:
    def __init__(self, path='/run/timetracking-loxone/bridge.sock'): self.path = path

    def call(self, operation, server=None, **data):
        message = {'operation':operation, **data}
        if server: message['server'] = server
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
                stream.settimeout(45)
                stream.connect(self.path)
                stream.sendall(json.dumps(message).encode()+b'\n')
                body=b''
                while not body.endswith(b'\n'):
                    chunk=stream.recv(65536)
                    if not chunk or len(body)+len(chunk)>2_000_000: raise ValueError()
                    body+=chunk
            result=json.loads(body)
            if not result.get('ok'): raise SyncError(result.get('error') if result.get('error') in MESSAGES else 'response')
            return result['data']
        except SyncError: raise
        except (OSError,ValueError,KeyError,TypeError,AttributeError): raise SyncError('bridge_unavailable') from None


def notify_change(db):
    # Delivery is deliberately outside the registration transaction. Failure here
    # never fails timekeeping; the periodic sweep repairs a missed notification.
    from datetime import datetime, timezone
    try:
        db.loxone_sync_meta.update_one({'_id':'queue'},
            {'$inc':{'sequence':1},'$set':{'requested_at':datetime.now(timezone.utc)}},upsert=True)
    except Exception:
        pass
