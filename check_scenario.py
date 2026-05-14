import json

scenario_name = "5.2.6 - basic login"
s = json.load(open(f'backend/scenarios/{scenario_name}.json'))

print(f"=== Scenario: {scenario_name} ===")
print(f"Base URL: {s.get('base_url')}")
print(f"\nSteps ({len(s['steps'])} total):")

for i, step in enumerate(s['steps'], 1):
    print(f"{i}. {step['name']}")
    print(f"   Action: {step['action']}")
    print(f"   Target: {step['target']}")
    if step.get('value'):
        print(f"   Value: {step['value'][:50]}")
    print()
