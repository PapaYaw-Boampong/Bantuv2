#!/bin/bash

# Install required packages
pip install -r requirements.txt

# Run the database setup test
python test_db_setup.py

# Clean up
pkill -f "uvicorn main:app"
