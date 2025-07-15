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

**Option 1: Docker Compose (Recommended)**

.. code-block:: bash

   docker-compose -f docker-compose-prod.yml up -d

**Option 2: Docker Direct**

.. code-block:: bash

   docker pull akshaychikhalkar/carla-driving-simulator-client:latest
   docker run -p 8081:8000 akshaychikhalkar/carla-driving-simulator-client:latest

**Option 3: Local Development**

.. code-block:: bash

   python run.py

Access the Application
---------------------

1. Open your browser and navigate to: http://localhost:8081
2. Log in with your credentials
3. Start exploring the CARLA simulation interface

For more details, see the README or the API Reference. 