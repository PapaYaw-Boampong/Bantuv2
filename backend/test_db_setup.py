import os
import subprocess
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def run_command(command):
    """Run shell command and return output"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

def test_database_setup():
    """
    Test the complete database setup process with comprehensive test cases:
    1. Database creation and connection
    2. Server startup and health check
    3. Basic CRUD operations
    4. Error scenarios
    5. Transaction handling
    """
    print("\nStarting comprehensive database test suite...\n")
    
    # 1. Database creation and connection
    print("1. Testing database creation and connection...")
    
    # Create test database
    test_db_name = "Bantu_db_test"
    create_db_cmd = f"createdb {test_db_name}"
    stdout, stderr = run_command(create_db_cmd)
    print(f"Database creation output: {stdout}")
    if stderr:
        print(f"Database creation error: {stderr}")
        return False
    
    # 2. Server startup and health check
    print("\n2. Testing server startup and health check...")
    
    # Start server with test database
    start_server_cmd = f"DBNAME={test_db_name} uvicorn main:app --reload &"
    run_command(start_server_cmd)
    time.sleep(5)  # Wait for server to start
    
    try:
        response = requests.get("http://localhost:8000/api/health")
        health_data = response.json()
        print(f"\nHealth check response: {json.dumps(health_data, indent=2)}")
        
        if health_data.get('status') != 'healthy':
            print("Health check failed!")
            return False
    except Exception as e:
        print(f"Failed to connect to health endpoint: {e}")
        return False
    
    # 3. Basic CRUD operations
    print("\n3. Testing CRUD operations...")
    
    # Create table
    create_table_cmd = """
python -c 'from db.connection import engine; 
engine.execute(\"CREATE TABLE IF NOT EXISTS test_users (\" 
\"id SERIAL PRIMARY KEY,\" 
\"name VARCHAR(100) NOT NULL,\" 
\"email VARCHAR(255) UNIQUE NOT NULL,\" 
\"created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)\")'
"""
    stdout, stderr = run_command(create_table_cmd)
    print(f"Table creation result: {stdout}")
    if stderr:
        print(f"Table creation error: {stderr}")
        return False
    
    # Insert data
    insert_data_cmd = """
python -c 'from db.connection import engine; 
engine.execute(\"INSERT INTO test_users (name, email) VALUES ('John Doe', 'john@example.com')\")'
"""
    stdout, stderr = run_command(insert_data_cmd)
    print(f"Insert data result: {stdout}")
    if stderr:
        print(f"Insert data error: {stderr}")
        return False
    
    # Update data
    update_data_cmd = """
python -c 'from db.connection import engine; 
engine.execute(\"UPDATE test_users SET name = 'Jane Doe' WHERE email = 'john@example.com'\")'
"""
    stdout, stderr = run_command(update_data_cmd)
    print(f"Update data result: {stdout}")
    if stderr:
        print(f"Update data error: {stderr}")
        return False
    
    # Delete data
    delete_data_cmd = """
python -c 'from db.connection import engine; 
engine.execute(\"DELETE FROM test_users WHERE email = 'john@example.com'\")'
"""
    stdout, stderr = run_command(delete_data_cmd)
    print(f"Delete data result: {stdout}")
    if stderr:
        print(f"Delete data error: {stderr}")
        return False
    
    # 4. Error scenarios
    print("\n4. Testing error scenarios...")
    
    # Test duplicate insert
    duplicate_insert_cmd = """
python -c 'from db.connection import engine; 
try: 
    engine.execute(\"INSERT INTO test_users (name, email) VALUES ('Test User', 'john@example.com')\")
except Exception as e:
    print(f'Error: {str(e)}')
'
"""
    stdout, stderr = run_command(duplicate_insert_cmd)
    print(f"Duplicate insert test result: {stdout}")
    if not stdout or "duplicate key" not in stdout.lower():
        print("Duplicate insert test failed!")
        return False
    
    # Test invalid query
    invalid_query_cmd = """
python -c 'from db.connection import engine; 
try: 
    engine.execute(\"SELECT * FROM non_existent_table\")
except Exception as e:
    print(f'Error: {str(e)}')
'
"""
    stdout, stderr = run_command(invalid_query_cmd)
    print(f"Invalid query test result: {stdout}")
    if not stdout or "relation" not in stdout.lower():
        print("Invalid query test failed!")
        return False
    
    # 5. Transaction handling
    print("\n5. Testing transaction handling...")
    
    # Test successful transaction
    success_transaction_cmd = """
python -c 'from db.connection import engine; 
with engine.begin() as conn:
    conn.execute(\"INSERT INTO test_users (name, email) VALUES ('Transaction Test', 'test@example.com')\")'
"""
    stdout, stderr = run_command(success_transaction_cmd)
    print(f"Success transaction result: {stdout}")
    if stderr:
        print(f"Success transaction error: {stderr}")
        return False
    
    # Test failed transaction (should rollback)
    failed_transaction_cmd = """
python -c 'from db.connection import engine; 
try:
    with engine.begin() as conn:
        conn.execute(\"INSERT INTO test_users (name, email) VALUES ('Failed Test', 'test@example.com')\")
        raise ValueError("Simulated error")
except Exception as e:
    print(f'Error: {str(e)}')
'
"""
    stdout, stderr = run_command(failed_transaction_cmd)
    print(f"Failed transaction test result: {stdout}")
    if not stdout or "simulated error" not in stdout.lower():
        print("Failed transaction test failed!")
        return False
    
    # 6. Connection pooling
    print("\n6. Testing connection pooling...")
    
    # Test multiple concurrent connections
    concurrent_test_cmd = """
python -c 'from db.connection import engine; 
import threading

def test_connection():
    with engine.connect() as conn:
        result = conn.execute(\"SELECT 1\")
        assert result.fetchone()[0] == 1

threads = []
for _ in range(10):
    t = threading.Thread(target=test_connection)
    threads.append(t)
    t.start()

for t in threads:
    t.join()'
"""
    stdout, stderr = run_command(concurrent_test_cmd)
    print(f"Connection pooling test result: {stdout}")
    if stderr:
        print(f"Connection pooling test error: {stderr}")
        return False
    
    print("\nAll tests completed successfully!")
    return True

if __name__ == "__main__":
    test_database_setup()
