#!/usr/bin/env python3
"""Private Unix socket only; a fresh PHP process reads current LoxBerry config."""
import json
import os
from pathlib import Path
import socketserver
import subprocess


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(3)
        try:
            data=self.rfile.readline(20001)
            if len(data)>20000 or not data.endswith(b'\n'):raise ValueError()
            request=json.loads(data)
            if not isinstance(request,dict):raise ValueError()
            result=subprocess.run(['/usr/bin/php','-d','display_errors=0',str(Path(__file__).with_name('loxone_adapter.php'))],
                input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=38,check=True)
            if len(result.stdout)>2_000_000:raise ValueError()
            response=json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            response={'ok':False,'error':'network'}
        except Exception:
            response={'ok':False,'error':'configuration'}
        try:self.wfile.write(json.dumps(response).encode()+b'\n')
        except OSError:pass


if __name__=='__main__':
    os.umask(0o077)
    path=Path('/run/timetracking-loxone/bridge.sock')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():path.unlink()
    with socketserver.UnixStreamServer(str(path),Handler) as server:
        path.chmod(0o600)
        server.serve_forever()
