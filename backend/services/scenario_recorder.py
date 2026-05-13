"""
Scenario Recorder Service
Records user interactions using Playwright and generates structured scenario steps
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
import os
from pathlib import Path


class ScenarioStep:
    """Represents a single step in a test scenario"""

    def __init__(
        self,
        name: str,
        action: str,
        target: str,
        value: Optional[str] = None,
        expected_result: Optional[str] = None
    ):
        self.name = name
        self.action = action  # 'click', 'type', 'navigate', 'wait', etc.
        self.target = target  # CSS selector or URL
        self.value = value  # For 'type' actions
        self.expected_result = expected_result

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "expected_result": self.expected_result
        }


class ScenarioRecorder:
    """Records and manages test scenarios"""

    def __init__(self, scenario_name: str, base_url: str):
        self.scenario_name = scenario_name
        self.base_url = base_url
        self.steps: List[ScenarioStep] = []
        self.start_time = datetime.utcnow()

    def add_step(
        self,
        name: str,
        action: str,
        target: str,
        value: Optional[str] = None,
        expected_result: Optional[str] = None
    ):
        """Add a step to the scenario"""
        step = ScenarioStep(
            name=name,
            action=action,
            target=target,
            value=value,
            expected_result=expected_result
        )
        self.steps.append(step)
        print(f"[Step {len(self.steps)}] {name}: {action} {target}")
        return step

    def save_to_file(self, filepath: Optional[str] = None) -> str:
        """Save scenario to JSON file"""
        if not filepath:
            import os
            scenarios_dir = Path(os.getenv("SCENARIOS_DIR", str(Path(__file__).parent.parent / "scenarios")))
            scenarios_dir.mkdir(exist_ok=True)
            filepath = scenarios_dir / f"{self.scenario_name}.json"

        scenario_data = {
            "name": self.scenario_name,
            "base_url": self.base_url,
            "user": "orcanos.tech",
            "created_at": self.start_time.isoformat(),
            "steps": [step.to_dict() for step in self.steps]
        }

        with open(filepath, 'w') as f:
            json.dump(scenario_data, f, indent=2)

        print(f"\n✓ Scenario saved to: {filepath}")
        return str(filepath)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.scenario_name,
            "base_url": self.base_url,
            "created_at": self.start_time.isoformat(),
            "steps": [step.to_dict() for step in self.steps]
        }

    def __repr__(self):
        return f"ScenarioRecorder(name={self.scenario_name}, steps={len(self.steps)})"


# Example scenario template
EXAMPLE_SCENARIO = {
    "name": "basic_workflow",
    "base_url": "https://app.orcanos.com/orcanos/web/",
    "user": "orcanos.tech",
    "steps": [
        {
            "name": "Login",
            "action": "navigate",
            "target": "https://app.orcanos.com/orcanos/web/Account/Login",
            "expected_result": "Login page displayed"
        },
        {
            "name": "Enter email",
            "action": "type",
            "target": "input[name='Email']",
            "value": "orcanos.tech",
            "expected_result": "Email entered"
        },
        {
            "name": "Enter password",
            "action": "type",
            "target": "input[name='Password']",
            "value": "PASSWORD_HERE",
            "expected_result": "Password entered"
        },
        {
            "name": "Click login button",
            "action": "click",
            "target": "button[type='submit']",
            "expected_result": "Logged in, redirected to dashboard"
        },
        {
            "name": "Wait for dashboard",
            "action": "wait",
            "target": ".dashboard-container",
            "value": "5000",
            "expected_result": "Dashboard loaded"
        },
        {
            "name": "Navigate to projects",
            "action": "click",
            "target": "a[href='/projects']",
            "expected_result": "Projects page displayed"
        },
        {
            "name": "Logout",
            "action": "click",
            "target": "button[data-action='logout']",
            "expected_result": "Logged out, redirected to login"
        }
    ]
}
