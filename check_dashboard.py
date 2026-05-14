import json
import os
from pathlib import Path

scenarios_dir = 'backend/scenarios'
files = [(f, os.path.getctime(f'{scenarios_dir}/{f}')) for f in os.listdir(scenarios_dir) if f.endswith('.json')]
latest = max(files, key=lambda x: x[1])[0]

print(f"Latest scenario: {latest}\n")
s = json.load(open(f'{scenarios_dir}/{latest}'))

print("All steps:")
for i, step in enumerate(s['steps'], 1):
    print(f"{i}. {step['name']}")
    print(f"   Action: {step['action']}")
    print(f"   Target: {step['target']}")
    if 'dashboard' in step['name'].lower():
        print("   ^^^ THIS IS THE DASHBOARD STEP ^^^")
    print()
