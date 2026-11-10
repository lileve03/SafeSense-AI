"""Single CPU worker, bounded waiting work and byte/entry/TTL bounded results."""
from collections import OrderedDict, deque
from threading import Condition, Thread
import json
import time


class QueueBusy(Exception):
    pass


class Superseded(Exception):
    pass


class InferenceQueue:
    def __init__(self, persist, cache_valid=lambda row: True, lookup=lambda identifier: None, cache_entries=6,
                 cache_bytes=32 * 1024 * 1024, cache_ttl=900, completed_lookup=None):
        self.condition = Condition()
        self.persist = persist
        self.cache_valid = cache_valid
        self.lookup = lookup
        self.completed_lookup=completed_lookup
        self.cache_entries, self.cache_bytes, self.cache_ttl = cache_entries, cache_bytes, cache_ttl
        self.active = {}
        self.pending = deque()
        self.running = None
        self.latest = OrderedDict()
        self.receipts = OrderedDict()
        self.cache = OrderedDict()
        self.cached_bytes = 0
        self.worker = None

    def _selection(self, client, sequence):
        if client is None:
            return
        if sequence < self.latest.get(client, -1):
            raise Superseded()
        self.latest[client] = sequence
        self.latest.move_to_end(client)
        while len(self.latest) > 256:
            self.latest.popitem(last=False)

    def _release(self, client, keep=None):
        if client is None:
            return
        for key, entry in list(self.active.items()):
            if key == keep:
                continue
            entry['owners'].discard(client)
            if entry is not self.running and not entry['owners'] and not entry['protected']:
                self.pending.remove(entry)
                self.active.pop(key)
                entry['row'].update(status='CANCELLED', cancellation_reason='Obsolete camera selection')
                self.persist(entry['row'])

    def release(self, client, sequence):
        with self.condition:
            self._selection(client, sequence)
            self._release(client)

    def _evict(self, key):
        _, size, _ = self.cache.pop(key)
        self.cached_bytes -= size

    def _prune(self):
        for key, (_, _, expires) in list(self.cache.items()):
            if expires <= time.monotonic():
                self._evict(key)

    def _receipt(self, client, sequence, key, row):
        if client:
            # Keep IDs only: retry idempotency must not retain 256 large pose results.
            self.receipts[client] = (sequence, key, row['id'])
            self.receipts.move_to_end(client)
            while len(self.receipts) > 256:
                self.receipts.popitem(last=False)

    def submit(self, key, row, work, client=None, sequence=0, reuse=True, force=False):
        with self.condition:
            self._selection(client, sequence)
            self._release(client, keep=key)
            self._prune()
            if key in self.active:
                entry = self.active[key]
                if client:
                    if client not in entry['owners'] and len(entry['owners']) >= 256:
                        raise QueueBusy()
                    entry['owners'].add(client)
                else:
                    entry['protected'] = True
                if client and entry is not self.running:
                    self.pending.remove(entry)
                    self.pending.appendleft(entry)
                self._receipt(client, sequence, key, entry['row'])
                return {**entry['row'], 'deduplicated': True}
            receipt = self.receipts.get(client) if client else None
            if receipt and receipt[:2] == (sequence, key):
                accepted = self.lookup(receipt[2])
                if accepted is not None:
                    return {**accepted, 'deduplicated': True, 'cache_hit':accepted.get('status')=='COMPLETED','cache_tier':'receipt' if accepted.get('status')=='COMPLETED' else None}
            if reuse and not force and key in self.cache:
                cached, _, _ = self.cache[key]
                if self.cache_valid(cached):
                    self.cache.move_to_end(key)
                    self._receipt(client, sequence, key, cached)
                    return {**cached, 'cache_hit': True,'cache_tier':'memory'}
                self._evict(key)
            if reuse and not force and self.completed_lookup is not None:
                cached=self.completed_lookup(key)
                if cached is not None and self.cache_valid(cached):
                    self._remember(key,cached)
                    self._receipt(client,sequence,key,cached)
                    return {**cached,'cache_hit':True,'cache_tier':'disk'}
            # At most one executing job plus two waiting jobs, including startup.
            if len(self.active) >= 3:
                raise QueueBusy()
            entry = {'key': key, 'row': row, 'work': work, 'owners': {client} if client else set(),
                     'protected': client is None, 'reuse': reuse}
            self.persist(row)
            self.active[key] = entry
            self._receipt(client, sequence, key, row)
            if client:
                self.pending.appendleft(entry)
            else:
                self.pending.append(entry)
            if self.worker is None:
                self.worker = Thread(target=self._drain, name='video-analysis', daemon=True)
                self.worker.start()
            self.condition.notify()
            return dict(row)

    def _drain(self):
        while True:
            with self.condition:
                while not self.pending:
                    self.condition.wait()
                entry = self.pending.popleft()
                self.running = entry
                entry['row']['status'] = 'RUNNING'
                self.condition.notify_all()
            try:
                entry['work']()
            except Exception as exc:
                # A persistence/cleanup failure must not permanently kill the worker.
                entry['row'].update(status='FAILED', error=type(exc).__name__)
                try:
                    self.persist(entry['row'])
                except Exception:
                    pass
            finally:
                with self.condition:
                    row, key = entry['row'], entry['key']
                    self.active.pop(key, None)
                    self.running = None
                    if entry['reuse'] and row['status'] == 'COMPLETED' and not row.get('result', {}).get('model_errors'):
                        self._remember(key,row)
                    self.condition.notify_all()

    def _remember(self,key,row):
        size=len(json.dumps(row).encode('utf-8'))
        if size>self.cache_bytes:return
        if key in self.cache:self._evict(key)
        self.cache[key]=(row,size,time.monotonic()+self.cache_ttl)
        self.cached_bytes+=size
        while len(self.cache)>self.cache_entries or self.cached_bytes>self.cache_bytes:self._evict(next(iter(self.cache)))

    def contains(self, identifier):
        with self.condition:
            return any(entry['row']['id'] == identifier for entry in self.active.values())
