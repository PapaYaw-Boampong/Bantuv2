#!/bin/bash

# Stop backend server
pkill -f "uvicorn main:app"

# Drop test tables
psql -c "DROP TABLE IF EXISTS test_table;" ${DBNAME:-Bantu_db}

# Drop database if it's a test database
if [ "${DBNAME}" = "Bantu_db_test" ]; then
    dropdb ${DBNAME}
fi

# Clean up Python processes
pkill -f "python -c"

# Clean up any remaining processes
pkill -f "uvicorn"

# Print cleanup status
echo "\nCleanup completed!"
echo "- Backend server stopped"
echo "- Test tables dropped"
echo "- Test database dropped (if test database)"
echo "- All Python processes cleaned up"
