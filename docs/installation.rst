Installation
============

Requirements
------------
- Python 3.11
- pip
- (Optional) Docker for containerized deployment

Supported Platforms
-------------------
- Windows 10+
- Ubuntu 22.04+

Steps
-----

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
      cd carla-driving-simulator-client

2. **Install dependencies:**

   .. code-block:: bash

      pip install -e .[dev,docs]

3. **(Optional) Build and run with Docker:**

   .. code-block:: bash

      docker-compose up --build

For more details, see the `README.md` and `DOCKER_README.md` files. 