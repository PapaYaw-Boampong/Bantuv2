#!/bin/bash

# Create .env file from example
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt

# Set up database
python -c "
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

engine = create_engine(f'postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB')
if not database_exists(engine.url):
    create_database(engine.url)
    print('Database created successfully')
else:
    print('Database already exists')
"

# Build and start containers
docker-compose up --build

# Instructions
echo "\nLocal development setup complete!"
echo "Access the application at:"
echo "- Frontend: http://localhost:5173"
echo "- Backend API: http://localhost:8000"
echo "- Model Inference: http://localhost:8001"
echo "\nStop the application with Ctrl+C"
