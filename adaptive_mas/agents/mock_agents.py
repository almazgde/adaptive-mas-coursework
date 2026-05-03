import asyncio
from typing import Dict, Any


class PlannerAgent:
    """Mock agent for planning tasks."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)  # Simulate processing
        return {"plan": f"Planned for {input_data}", "agent": "PlannerAgent"}


class ResearcherAgent:
    """Mock agent for researching information."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {"research": f"Researched {input_data}", "agent": "ResearcherAgent"}


class CriticAgent:
    """Mock agent for critiquing results."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {"critique": f"Critiqued {input_data}", "agent": "CriticAgent"}


class SynthesizerAgent:
    """Mock agent for synthesizing information."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {"synthesis": f"Synthesized {input_data}", "agent": "SynthesizerAgent"}