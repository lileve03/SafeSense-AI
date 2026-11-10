"""Ensure direct backend startup and launcher agree without exposing real credentials."""
from pathlib import Path
import os,sys,json,tempfile,subprocess,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.start_services import load_local_environment

class BackendTelegramEnvironment(unittest.TestCase):
 def test_explicit_environment_precedes_file(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'.env';path.write_text('TELEGRAM_MODE=test\nTELEGRAM_BOT_TOKEN=fake-file-token\nTELEGRAM_TEST_CHAT_ID=-100123\n',encoding='utf-8')
   with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'fake-existing-token'},clear=True):
    load_local_environment(path)
    self.assertEqual(os.environ['TELEGRAM_BOT_TOKEN'],'fake-existing-token')
    self.assertEqual(os.environ['TELEGRAM_MODE'],'test')
 def test_chat_alias_requires_explicit_test_mode(self):
  for mode in ('disabled','staff','test'):
   with patch.dict(os.environ,{'TELEGRAM_MODE':mode,'TELEGRAM_CHAT_ID':'-100123'},clear=True):
    load_local_environment(ROOT/'runtime/does-not-exist.env')
    self.assertEqual(bool(os.getenv('TELEGRAM_TEST_CHAT_ID')),mode=='test')
 def test_explicit_test_recipient_wins_alias(self):
  with patch.dict(os.environ,{'TELEGRAM_MODE':'test','TELEGRAM_CHAT_ID':'generic','TELEGRAM_TEST_CHAT_ID':'explicit'},clear=True):
   load_local_environment(ROOT/'runtime/does-not-exist.env')
   self.assertEqual(os.environ['TELEGRAM_TEST_CHAT_ID'],'explicit')
 def test_direct_backend_import_loads_project_configuration(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory);(path/'.env').write_text('TELEGRAM_MODE=test\nTELEGRAM_BOT_TOKEN=fake-startup-token\nTELEGRAM_TEST_CHAT_ID=-100123\n',encoding='utf-8')
   code="from pathlib import Path; import scripts.start_services as config; config.ROOT=Path(__import__('sys').argv[1]); from backend.main import app; from backend import notifications; status=notifications.status(); assert status['mode']=='test' and status['test_configured']; print('Direct backend startup configuration: PASS')"
   env={k:v for k,v in os.environ.items() if not k.startswith('TELEGRAM_')}
   env.update(SAFESENSE_DB_PATH=str(path/'test.sqlite3'))
   result=subprocess.run([sys.executable,'-c',code,str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertNotIn('fake-startup-token',result.stdout)

if __name__=='__main__':unittest.main(verbosity=2)
