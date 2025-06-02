from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.config import load_config, save_config

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize simulation runner
runner = SimulationRunner()

class SimulationRequest(BaseModel):
    scenario: str
    debug: bool = False
    report: bool = False

class ConfigUpdate(BaseModel):
    config_data: dict

@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available scenarios"""
    ScenarioRegistry.register_all()
    return {"scenarios": ScenarioRegistry.get_available_scenarios()}

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return runner.config

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration"""
    try:
        save_config(config_update.config_data, runner.config_file)
        runner.config = load_config(runner.config_file)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    """Start simulation with given parameters"""
    try:
        # Setup logger
        runner.setup_logger(request.debug)
        
        # Run the scenario
        success, message = runner.run_single_scenario(request.scenario)
        
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 