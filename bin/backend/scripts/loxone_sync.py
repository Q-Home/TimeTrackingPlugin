#!/usr/bin/env python3
"""One externally scheduled sweep. No scheduler runs in a Gunicorn worker."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pymongo import MongoClient
from app.hr.service import HRService
from app.loxone_sync.service import SyncService
from app.loxone_sync.bridge import SyncError


def main():
    try:
        db=MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=5000).get_default_database()
        SyncService(db,HRService(db)).run()
        return 0
    except SyncError:
        # Specific sanitized errors are kept per employee in the database.
        print('Loxone-synchronisatie bezet of niet beschikbaar; volgende cronronde probeert opnieuw.')
        return 0
    except Exception:
        print('Loxone-synchronisatie kon niet worden uitgevoerd; tijdregistratie blijft actief.')
        return 1


if __name__=='__main__':raise SystemExit(main())
