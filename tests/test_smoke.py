"""HTTP smoke test against a fresh, isolated temporary application instance."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

APP=Path(__file__).resolve().parents[1]/'app.py'

def ephemeral_port():
    sock=socket.socket()
    sock.bind(('127.0.0.1',0))
    p=sock.getsockname()[1]
    sock.close()
    return p

class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.port=ephemeral_port()
        env=dict(os.environ,SIGNAGE_DATA_DIR=cls.temp.name,SIGNAGE_HOST='127.0.0.1',SIGNAGE_PORT=str(cls.port),INITIAL_ADMIN_PASSWORD='temporary-test-password-123!',FRAME_ANCESTORS='http://127.0.0.1:8097',COOKIE_SECURE='true')
        cls.process=subprocess.Popen([sys.executable,str(APP)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError('application exited: '+cls.process.stderr.read().decode())
            try:
                conn=http.client.HTTPConnection('127.0.0.1',cls.port,timeout=.5)
                conn.request('GET','/health')
                resp=conn.getresponse()
                resp.read()
                if resp.status==200:
                    conn.close()
                    break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('application did not start')
    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.temp.cleanup()
    def fetch(self,path,method='GET',body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        conn.request(method,path,body=body,headers=headers or {})
        res=conn.getresponse()
        data=res.read()
        h=dict(res.getheaders())
        status=res.status
        conn.close()
        return status,h,data
    def test_dashboard_frame_header(self):
        status,headers,body=self.fetch('/')
        self.assertEqual(status,200)
        self.assertIn(b'SERKAN SIGNAGE',body)
        self.assertIn('http://127.0.0.1:8097',headers.get('Content-Security-Policy',''))
        self.assertNotIn('X-Frame-Options',headers)
    def test_admin_rejects_unauthorized_embedding(self):
        status,headers,body=self.fetch('/serkan')
        self.assertEqual(status,200)
        self.assertEqual(headers.get('X-Frame-Options'),'DENY')
        self.assertIn(b'Administratorpasswort',body)
    def test_safe_new_install(self):
        status,_,body=self.fetch('/api/state')
        self.assertEqual(status,200)
        data=json.loads(body)
        self.assertEqual(data['city'],'Berlin')
        self.assertEqual(data['meals'],['—']*7)
        self.assertEqual(data['photos'],[])
        self.assertLessEqual(len(data['weather']),7)
        self.assertEqual(len((Path(self.temp.name)/'secret').read_text().strip()),64)
    def test_login_cookie_secure(self):
        body=b'password=temporary-test-password-123%21'
        status,headers,_=self.fetch('/login','POST',body,{'Content-Type':'application/x-www-form-urlencoded'})
        self.assertEqual(status,303)
        self.assertIn('Secure',headers.get('Set-Cookie',''))
        self.assertIn('HttpOnly',headers.get('Set-Cookie',''))
    def test_upload_is_authenticated(self):
        status,_,_=self.fetch('/upload','POST',b'foo=bar',{'Content-Type':'application/x-www-form-urlencoded'})
        self.assertEqual(status,403)

if __name__=='__main__':unittest.main()
