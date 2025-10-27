#!/bin/bash

# SentinelFlow Service Stop Script
# Gracefully stops all running services

set -e

echo "=========================================="
echo "🛑 Stopping SentinelFlow Services"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $service_name (PID: $PID)...${NC}"
            kill $PID
            sleep 2
            
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                echo -e "${YELLOW}Force stopping $service_name...${NC}"
                kill -9 $PID
            fi
            
            echo -e "${GREEN}✓${NC} $service_name stopped"
        else
            echo -e "${YELLOW}⚠${NC} $service_name not running"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠${NC} $service_name PID file not found"
    fi
}

# Stop all services
stop_service "Detection Engine" "logs/detection_engine.pid"
stop_service "Explanation Service" "logs/explanation_service.pid"
stop_service "Dashboard" "logs/dashboard.pid"
stop_service "Feedback Loop" "logs/feedback_loop.pid"

# Clean up any remaining Python processes
echo -e "\n${YELLOW}Cleaning up remaining processes...${NC}"
pkill -f "detection_engine.main" 2>/dev/null || true
pkill -f "explanation_service.main" 2>/dev/null || true
pkill -f "dashboard.main" 2>/dev/null || true
pkill -f "feedback_loop.main" 2>/dev/null || true

echo -e "\n=========================================="
echo -e "${GREEN}✓ All services stopped successfully!${NC}"
echo "=========================================="

echo -e "\n📝 Log files preserved in logs/ directory"
echo -e "\nTo restart services, run:"
echo -e "  ./start_services.sh"