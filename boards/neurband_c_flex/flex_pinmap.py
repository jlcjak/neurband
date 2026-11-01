"""Electrode flex rev C.2: which pod electrode lands on which tail finger.

E<k>P is pod k's proximal electrode (flex Y = -10), E<k>N its distal one (Y = +10); the middle electrode of
every pod is BIAS_E. Any pod may use any J1 pair, in either orientation, because the host maps channels
(host/neurband_ble.py POD_MAP; docs/firmware_c.md "Channel map"). This assignment is the one that makes the root fan-in planar: the trunk lanes
turn down into the tail in lane order, so no two signal lines cross.
Main-board side (same physical finger numbers): J1 n mates with the main board's J1 pin n.
"""
TAIL = {1: 'GND', 2: 'BIAS_E', 19: 'BIAS_E', 20: 'GND',
        3: 'E5P', 4: 'E5N', 5: 'E6P', 6: 'E6N', 7: 'E7P', 8: 'E7N', 9: 'E8P', 10: 'E8N',
        11: 'E4N', 12: 'E4P', 13: 'E1P', 14: 'E1N', 15: 'E2P', 16: 'E2N', 17: 'E3P', 18: 'E3N'}
