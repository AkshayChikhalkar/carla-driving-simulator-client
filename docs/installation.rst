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

3. **(Recommended) Run with Docker Compose:**

   .. code-block:: bash

      docker-compose -f docker-compose-prod.yml up -d

4. **(Alternative) Run with Docker directly:**

   .. code-block:: bash

      docker pull akshaychikhalkar/carla-driving-simulator-client:latest
      docker run -p 8081:8000 akshaychikhalkar/carla-driving-simulator-client:latest

5. **Access the application:**

   Open your browser and navigate to: http://localhost:8081

For more details, see the `README.md` and `DOCKER_README.md` files. 