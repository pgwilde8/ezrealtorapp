#!/bin/bash
# EZRealtor.app Server Startup Script

# Set environment variables
export PYTHONPATH=/root/ezrealtor/ezadmin
export DATABASE_URL="postgresql+asyncpg://ezrealtor_user:ezrealtor_pass@localhost:5432/ezrealtor_db"

# Start the server using the virtual environment python
exec /root/ezrealtor/ezadmin/venv/bin/python3 /root/ezrealtor/ezadmin/app/main.py