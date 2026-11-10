"""SafeSense Phase 6: interactive simulation of private-zone mmWave/SOS events.

This module does NOT read physical mmWave hardware and DOES NOT dispatch emergencies.
All events use source='simulation'. No image or audio is captured or saved.
"""
import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EVENTS = {
    '1': ('presence', 'Simulated mmWave presence'),
    '2': ('normal_motion', 'Simulated mmWave motion'),
    '3': ('fall', 'Simulated mmWave fall candidate'),
    '4': ('scream', 'Simulated acoustic scream candidate'),
    '5': ('impact', 'Simulated acoustic impact candidate'),
    '6': ('sos', 'Simulated SOS test button'),
}


def api_request(base_url: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = Request(base_url.rstrip('/') + path, data=data,
                  headers={'Content-Type': 'application/json'} if data else {},
                  method='POST' if data else 'GET')
    with urlopen(req, timeout=5) as response:
        return json.load(response)


def send_test_event(base_url: str, zone: str, event_type: str, confidence: float = 0.95):
    if event_type not in [event[0] for event in EVENTS.values()]:
        raise ValueError(f'Unsupported test event: {event_type}')
    if not 0 <= confidence <= 1:
        raise ValueError('confidence must be between 0 and 1')
    return api_request(base_url, '/event', {
        'zone': zone, 'type': event_type,
        'confidence': confidence, 'source': 'simulation', 'processing_mode': 'simulation',
        'sensor_modality': 'acoustic' if event_type in ('scream','impact') else 'sos' if event_type == 'sos' else 'radar'
    })


def main():
    parser = argparse.ArgumentParser(description='SafeSense private-area simulation ONLY')
    parser.add_argument('--api', default='http://127.0.0.1:8000')
    parser.add_argument('--zone', default='Demo-Private-A')
    parser.add_argument('--self-test', action='store_true',
                        help='Send fall + scream within 5 seconds (no actual hardware)')
    args = parser.parse_args()
    try:
        registered = api_request(args.api, '/zones')
        alias = {'Demo-Private-A': 'ZONE_TOILET_BLINDSPOT',
                 'Toilet Block B': 'ZONE_TOILET_BLINDSPOT',
                 'Toilet Entrance': 'ZONE_TOILET_BLINDSPOT'}
        zone_id = alias.get(args.zone, args.zone)
        zone = next((z for z in registered if z['id'] == zone_id), None)
        if zone is None or zone['zone_type'] != 'PRIVATE':
            raise ValueError(f'Zone must be registered as PRIVATE: {args.zone}')
    except (HTTPError, URLError, ValueError, TimeoutError) as exc:
        print(f'Cannot validate PRIVATE zone / backend: {exc}', file=sys.stderr)
        return 1

    print('SIMULATION ONLY | No hardware connected | No real SOS dispatch')
    print(f'Backend: {args.api} | PRIVATE zone: {zone_id}')

    def show(event_type):
        result = send_test_event(args.api, args.zone, event_type)
        event = result['event']; incident = result['incident']
        print(f"  event={event['type']}  level={event['level']}  reason={event['reason']}")
        if incident:
            print(f"  TEST INCIDENT: {incident['id']} ({incident['status']})")

    if args.self_test:
        try:
            show('fall')
            time.sleep(0.3)
            show('scream')
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f'API request failed: {exc}', file=sys.stderr)
            return 1
        return 0

    while True:
        print('\nPRIVATE-AREA TEST CONSOLE')
        for key, (_, label) in EVENTS.items():
            print(f'  {key} = {label}')
        print('  7 = Show backend incidents | q = Quit')
        choice = input('Select: ').strip().lower()
        if choice == 'q':
            return 0
        try:
            if choice in EVENTS:
                if choice == '6' and input('Confirm TEST SOS event (type TEST): ').strip() != 'TEST':
                    print('Cancelled.'); continue
                show(EVENTS[choice][0])
            elif choice == '7':
                state = api_request(args.api, '/state')
                for incident in state['incidents'][:10]:
                    print(f"  [{incident['level']}] {incident['zone']} {incident['status']} {incident['id']}")
            else:
                print('Unknown option.')
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f'API request failed: {exc}')


if __name__ == '__main__':
    sys.exit(main())
