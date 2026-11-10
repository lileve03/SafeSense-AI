"""Simple, explainable temporal pose heuristics. NOT a validated fall detector."""
from collections import deque
from dataclasses import dataclass, field
from math import hypot

@dataclass
class Observation:
    time: float
    center: tuple[float, float]  # normalized center (x,y)
    horizontal: bool
    upright: bool
    reliable: bool

@dataclass
class PersonHistory:
    samples: deque = field(default_factory=lambda: deque(maxlen=90))
    last_event_time: dict = field(default_factory=dict)

class TemporalAnalyzer:
    def __init__(self, motion_threshold=0.14, motion_window=1.2,
                 fall_window=2.5, cooldown=8.0):
        self.motion_threshold = motion_threshold
        self.motion_window = motion_window
        self.fall_window = fall_window
        self.cooldown = cooldown
        self.histories = {}

    def update(self, track_id, obs: Observation):
        h = self.histories.setdefault(track_id, PersonHistory())
        h.samples.append(obs)
        while h.samples and obs.time - h.samples[0].time > max(self.motion_window, self.fall_window) + .5:
            h.samples.popleft()
        events = []
        reliable = [s for s in h.samples if s.reliable]
        if len(reliable) < 4:
            return events

        # Speed is normalized frame displacement per second; NOT meters/second.
        speeds = []
        for a, b in zip(reliable, reliable[1:]):
            dt = b.time - a.time
            if .04 <= dt <= .8 and b.time >= obs.time-self.motion_window:
                speeds.append(hypot(b.center[0]-a.center[0], b.center[1]-a.center[1])/dt)
        elevated = sum(s >= self.motion_threshold for s in speeds)
        if (len(speeds) >= 4 and elevated/len(speeds) >= .7
                and obs.time - h.last_event_time.get('rapid_motion', -1e9) >= self.cooldown):
            h.last_event_time['rapid_motion'] = obs.time
            events.append('rapid_motion')

        # Require earlier upright evidence AND recent consecutive horizontal evidence.
        # Motion or horizontal posture alone is NOT sufficient to infer a fall.
        earlier = [s for s in reliable if obs.time-self.fall_window <= s.time <= obs.time-.45]
        latest = [s for s in reliable if obs.time-.6 <= s.time <= obs.time]
        had_upright = any(s.upright for s in earlier)
        recent_horizontal = (len(latest) >= 3 and sum(s.horizontal for s in latest[-4:]) >= 3)
        if (had_upright and recent_horizontal
                and obs.time-h.last_event_time.get('fall', -1e9) >= self.cooldown):
            h.last_event_time['fall'] = obs.time
            events.append('fall')
        return events

    def expire(self, now, max_age=4.0):
        self.histories = {k:v for k,v in self.histories.items()
                          if v.samples and now-v.samples[-1].time < max_age}
