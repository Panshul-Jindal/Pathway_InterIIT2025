#!/bin/bash

# SentinelFlow Service Startup Script
# This script starts all services in the correct order

set -e

echo "=========================================="
echo "🚀 Starting SentinelFlow Services"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Redis is running
echo -e "\n${YELLOW}[1/6]${NC} Checking Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis started successfully"
    else
        echo -e "${RED}✗${NC} Failed to start Redis. Please start it manually."
        exit 1
    fi
fi

# Create log directory
mkdir -p logs

# Start Detection Engine
echo -e "\n${YELLOW}[2/6]${NC} Starting Detection Engine..."
cd detection_engine
python main.py > ../logs/detection_engine.log 2>&1 &
DETECTION_PID=$!
echo $DETECTION_PID > ../logs/detection_engine.pid
echo -e "${GREEN}✓${NC} Detection Engine started (PID: $DETECTION_PID)"
cd ..
sleep 3

# Start Explanation Service
echo -e "\n${YELLOW}[3/6]${NC} Starting Explanation Service..."
cd explanation_service
uvicorn main:app --host 0.0.0.0 --port 8001 > ../logs/explanation_service.log 2>&1 &
EXPLANATION_PID=$!
echo $EXPLANATION_PID > ../logs/explanation_service.pid
echo -e "${GREEN}✓${NC} Explanation Service started (PID: $EXPLANATION_PID)"
cd ..
sleep 3

# Start Dashboard
echo -e "\n${YELLOW}[4/6]${NC} Starting Dashboard..."
cd dashboard
uvicorn main:app --host 0.0.0.0 --port 8002 > ../logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > ../logs/dashboard.pid
echo -e "${GREEN}✓${NC} Dashboard started (PID: $DASHBOARD_PID)"
cd ..
sleep 3

# Start Feedback Loop
echo -e "\n${YELLOW}[5/6]${NC} Starting Feedback Loop..."
cd feedback_loop
python main.py > ../logs/feedback_loop.log 2>&1 &
FEEDBACK_PID=$!
echo $FEEDBACK_PID > ../logs/feedback_loop.pid
echo -e "${GREEN}✓${NC} Feedback Loop started (PID: $FEEDBACK_PID)"
cd ..
sleep 2

# Run integration tests
echo -e "\n${YELLOW}[6/6]${NC} Running integration tests..."
sleep 5  # Give services time to initialize
python tests/integration_test.py

echo -e "\n=========================================="
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo "=========================================="

echo -e "\n📊 Service Status:"
echo "  • Detection Engine:     PID $DETECTION_PID"
echo "  • Explanation Service:  PID $EXPLANATION_PID (http://localhost:8001)"
echo "  • Dashboard:            PID $DASHBOARD_PID (http://localhost:8002)"
echo "  • Feedback Loop:        PID $FEEDBACK_PID"

echo -e "\n📝 Log files:"
echo "  • Detection Engine:     logs/detection_engine.log"
echo "  • Explanation Service:  logs/explanation_service.log"
echo "  • Dashboard:            logs/dashboard.log"
echo "  • Feedback Loop:        logs/feedback_loop.log"

echo -e "\n🌐 Access Points:"
echo "  • Dashboard UI:         http://localhost:8002"
echo "  • Explanation API:      http://localhost:8001/health"

echo -e "\n🛑 To stop all services, run:"
echo "  ./stop_services.sh"

echo -e "\n📊 To monitor logs, run:"
echo "  tail -f logs/detection_engine.log"
echo "  tail -f logs/dashboard.log"

# Keep script running to show logs
echo -e "\n${YELLOW}Press Ctrl+C to view live logs...${NC}"
sleep 3
tail -f logs/detection_engine.log