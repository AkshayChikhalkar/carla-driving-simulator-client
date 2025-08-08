System Architecture
===================

The CARLA Driving Simulator Client is organized into modular components:

- **Control Layer:** Handles vehicle control and user input (see `carla_simulator/control/`).
- **Core Layer:** Manages simulation logic, scenarios, and world state (see `carla_simulator/core/`).
- **Database Layer:** Handles data persistence and models (see `carla_simulator/database/`).
- **Visualization Layer:** Provides real-time and web-based visualization (see `carla_simulator/visualization/`).
- **Scenarios:** Contains scenario definitions and logic (see `carla_simulator/scenarios/`).

.. note::
   See the diagrams in :doc:`diagrams` for a visual overview.

For more details, refer to the `system_architecture.md` and related files in the project root. 
