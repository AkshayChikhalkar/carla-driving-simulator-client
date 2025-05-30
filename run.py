#!/usr/bin/env python
"""
Entry point script for the CARLA Driving Simulator.
"""

import sys
from src.main import main

if __name__ == '__main__':
    # Pass all command line arguments to main()
    main(sys.argv[1:]) 