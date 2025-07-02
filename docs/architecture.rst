System Architecture
===================

The CARLA Driving Simulator Client is organized into modular components:

- **Control Layer:** Handles vehicle control and user input (see `src/control/`).
- **Core Layer:** Manages simulation logic, scenarios, and world state (see `src/core/`).
- **Database Layer:** Handles data persistence and models (see `src/database/`).
- **Visualization Layer:** Provides real-time and web-based visualization (see `src/visualization/`).
- **Scenarios:** Contains scenario definitions and logic (see `src/scenarios/`).

.. note::
   See the diagrams in :doc:`diagrams` for a visual overview.

For more details, refer to the `system_architecture.md` and related files in the project root. 