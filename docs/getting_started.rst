Getting Started
===============

Welcome to the CARLA Driving Simulator Client!

This guide will help you get started with installation, setup, and running your first simulation.

Installation
------------

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
      cd carla-driving-simulator-client

2. **Install dependencies:**

   .. code-block:: bash

      pip install -e .[dev,docs]

3. **(Optional) Build documentation locally:**

   .. code-block:: bash

      cd docs
      sphinx-build -b html . _build/html

Quickstart
----------

To run the simulator client:

.. code-block:: bash

   python run.py

For more details, see the README or the API Reference. 