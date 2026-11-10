"""Deterministic concurrency/resource tests; no model inference or external delivery."""
import copy
import sys
import time
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.inference_queue import InferenceQueue, QueueBusy, Superseded


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.gates = []
        self.executed = []
        self.queue = InferenceQueue(lambda row: self.rows.update({row['id']: copy.deepcopy(row)}))
        self.queue.lookup = lambda identifier: self.rows.get(identifier)

    def tearDown(self):
        for gate in self.gates:
            gate.set()
        self.idle()

    def idle(self):
        with self.queue.condition:
            self.assertTrue(self.queue.condition.wait_for(lambda: not self.queue.active, timeout=5))

    def submit(self, key, client=None, seq=0, gate=None, fail=False, **kwargs):
        row = {'id': key + '-job', 'status': 'QUEUED'}
        def work():
            self.executed.append(key)
            if gate:
                self.assertTrue(gate.wait(5))
            if fail:
                raise ValueError('deliberate failure')
            row.update(status='COMPLETED', result={'actual': key})
            self.queue.persist(row)
        return self.queue.submit(key, row, work, client, seq, **kwargs)

    def blocked(self, client=None):
        gate = Event(); self.gates.append(gate)
        self.submit('running', client, 1, gate)
        with self.queue.condition:
            self.assertTrue(self.queue.condition.wait_for(lambda: self.queue.running is not None, timeout=2))
        return gate

    def test_concurrent_duplicates_execute_once(self):
        gate = self.blocked()
        with ThreadPoolExecutor(max_workers=12) as pool:
            rows = list(pool.map(lambda _: self.submit('running'), range(30)))
        self.assertEqual({row['id'] for row in rows}, {'running-job'})
        self.assertTrue(all(row['deduplicated'] for row in rows))
        self.assertEqual(len(self.queue.active), 1)
        gate.set(); self.idle()
        self.assertEqual(self.executed, ['running'])

    def test_switch_cancels_only_own_waiting_job_and_prioritizes_latest(self):
        gate = self.blocked('panel')
        self.submit('obsolete', 'panel', 2)
        self.submit('unrelated')
        self.submit('latest', 'panel', 3)
        self.assertEqual(self.rows['obsolete-job']['status'], 'CANCELLED')
        self.assertEqual(self.queue.running['row']['id'], 'running-job')
        self.assertEqual(len(self.queue.active), 3)
        gate.set(); self.idle()
        self.assertEqual(self.executed, ['running', 'latest', 'unrelated'])

    def test_shared_work_and_unscoped_jobs_survive_saturation(self):
        gate = self.blocked()
        self.submit('shared', 'one', 1)
        self.submit('shared', 'two', 1)
        self.submit('protected')
        with self.assertRaises(QueueBusy):
            self.submit('new', 'one', 2)
        self.assertEqual(len(self.queue.active), 3)
        self.assertEqual(self.rows['shared-job']['status'], 'QUEUED')
        self.queue.release('two', 2)
        self.assertEqual(self.rows['shared-job']['status'], 'CANCELLED')
        self.submit('new', 'one', 2)
        gate.set(); self.idle()
        self.assertIn('protected', self.executed)
        self.assertNotIn('shared', self.executed)

    def test_out_of_order_requests_cannot_replace_new_selection(self):
        self.blocked()
        self.submit('latest', 'panel', 4)
        with self.assertRaises(Superseded):
            self.submit('old', 'panel', 3)
        with self.assertRaises(Superseded):
            self.queue.release('panel', 3)
        self.assertIn('latest', self.queue.active)

    def test_completed_cache_and_force_rerun(self):
        self.submit('same'); self.idle()
        row = self.submit('same')
        self.assertTrue(row['cache_hit'])
        self.assertEqual(self.executed, ['same'])
        self.submit('same', force=True); self.idle()
        self.assertEqual(self.executed, ['same', 'same'])

    def test_force_retry_is_idempotent_even_after_completion(self):
        self.submit('same', 'panel', 1, force=True); self.idle()
        retry = self.submit('same', 'panel', 1, force=True)
        self.assertTrue(retry['deduplicated'])
        self.assertEqual(self.executed, ['same'])
        self.submit('same', 'panel', 2, force=True); self.idle()
        self.assertEqual(self.executed, ['same', 'same'])

    def test_cache_entry_bytes_ttl_and_artifact_invalidation(self):
        self.queue.cache_entries = 2
        for key in ['a', 'b', 'c']:
            self.submit(key); self.idle()
        self.assertEqual(list(self.queue.cache), ['b', 'c'])
        self.assertLessEqual(self.queue.cached_bytes, self.queue.cache_bytes)
        row, size, _ = self.queue.cache['c']
        self.queue.cache['c'] = (row, size, time.monotonic() - 1)
        self.submit('c'); self.idle()
        self.assertEqual(self.executed.count('c'), 2)
        self.queue.cache_valid = lambda _: False
        self.submit('c'); self.idle()
        self.assertEqual(self.executed.count('c'), 3)
        self.queue.cache_bytes = 1
        self.submit('large'); self.idle()
        self.assertNotIn('large', self.queue.cache)

    def test_failure_releases_capacity_and_worker_recovers(self):
        self.submit('failed', fail=True); self.idle()
        self.assertEqual(self.rows['failed-job']['status'], 'FAILED')
        self.assertNotIn('failed', self.queue.cache)
        self.submit('recovery'); self.idle()
        self.assertEqual(self.rows['recovery-job']['status'], 'COMPLETED')

    def test_live_samples_are_not_cached_and_release_never_stops_running(self):
        gate = self.blocked('panel')
        self.queue.release('panel', 2)
        self.assertIsNotNone(self.queue.running)
        gate.set(); self.idle()
        self.submit('live', reuse=False); self.idle()
        self.submit('live', reuse=False); self.idle()
        self.assertEqual(self.executed.count('live'), 2)
        self.assertNotIn('live', self.queue.cache)


if __name__ == '__main__':
    unittest.main(verbosity=2)
