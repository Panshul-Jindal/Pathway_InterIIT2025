# dashboard/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import json
import uuid
from typing import Dict, List
from shared.redis_client import redis_client
from shared.schemas import Alert, Feedback
import datetime

app = FastAPI(title="SentinelFlow Dashboard")

# Mount static files and templates (if they exist)
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)


class KillSwitch:
    """Kill switch to stop all fraud detection processing"""
    def __init__(self):
        self.is_active = False
        self.activation_time = None
        self.activated_by = None
    
    async def activate(self, analyst_id: str = "unknown"):
        """Activate kill switch and broadcast to all services"""
        self.is_active = True
        self.activation_time = datetime.datetime.now()
        self.activated_by = analyst_id
        
        # Broadcast to detection engine and other services
        await redis_client.publish('kill_switch', json.dumps({
            'active': True,
            'timestamp': self.activation_time.isoformat(),
            'activated_by': analyst_id
        }))
        
        print(f"🛑 KILL SWITCH ACTIVATED by {analyst_id}")
        return True
    
    async def deactivate(self, analyst_id: str = "unknown"):
        """Deactivate kill switch"""
        self.is_active = False
        
        # Broadcast deactivation
        await redis_client.publish('kill_switch', json.dumps({
            'active': False,
            'timestamp': datetime.datetime.now().isoformat(),
            'deactivated_by': analyst_id
        }))
        
        print(f"✅ Kill switch deactivated by {analyst_id}")
        return True
    
    def get_status(self):
        """Get current kill switch status"""
        return {
            'active': self.is_active,
            'activation_time': self.activation_time.isoformat() if self.activation_time else None,
            'activated_by': self.activated_by
        }


manager = ConnectionManager()
kill_switch = KillSwitch()

# **FIX 1: Use Redis for persistence instead of memory**
# alerts_db: Dict[str, Alert] = {}  # OLD: Memory-only storage


async def store_alert(alert: Alert):
    """Store alert in Redis"""
    await redis_client.setex(
        f"alert:{alert.alert_id}",
        86400,  # 24 hour TTL
        json.dumps(alert.dict(), default=str)
    )


async def get_alert(alert_id: str) -> Alert:
    """Retrieve alert from Redis"""
    data = await redis_client.get(f"alert:{alert_id}")
    if data:
        return Alert(**json.loads(data))
    return None


@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>SentinelFlow Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                h1 {
                    color: #333;
                    border-bottom: 3px solid #667eea;
                    padding-bottom: 10px;
                }
                .controls {
                    margin: 20px 0;
                    padding: 15px;
                    background: #f5f5f5;
                    border-radius: 5px;
                }
                .kill-switch {
                    padding: 10px 20px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .kill-switch.inactive {
                    background: #dc3545;
                    color: white;
                }
                .kill-switch.active {
                    background: #28a745;
                    color: white;
                }
                .kill-switch:hover {
                    transform: scale(1.05);
                }
                #status {
                    display: inline-block;
                    margin-left: 20px;
                    padding: 8px 15px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                #status.running {
                    background: #d4edda;
                    color: #155724;
                }
                #status.stopped {
                    background: #f8d7da;
                    color: #721c24;
                }
                .alert-card {
                    border: 2px solid #ddd;
                    margin: 15px 0;
                    padding: 20px;
                    border-radius: 8px;
                    background: white;
                    transition: all 0.3s;
                }
                .alert-card:hover {
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }
                .alert-card.high-risk {
                    border-color: #dc3545;
                    background: #fff5f5;
                }
                .alert-card.medium-risk {
                    border-color: #ffc107;
                    background: #fffef5;
                }
                .alert-card.low-risk {
                    border-color: #28a745;
                    background: #f5fff5;
                }
                .alert-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                .risk-badge {
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                .risk-badge.high {
                    background: #dc3545;
                    color: white;
                }
                .risk-badge.medium {
                    background: #ffc107;
                    color: #333;
                }
                .risk-badge.low {
                    background: #28a745;
                    color: white;
                }
                .transaction-details {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                    margin: 15px 0;
                    padding: 15px;
                    background: #f9f9f9;
                    border-radius: 5px;
                }
                .detail-item {
                    padding: 5px;
                }
                .detail-label {
                    font-weight: bold;
                    color: #666;
                }
                .explanation {
                    margin: 15px 0;
                    padding: 15px;
                    background: #e3f2fd;
                    border-left: 4px solid #2196f3;
                    border-radius: 4px;
                    white-space: pre-wrap;
                }
                .actions {
                    margin-top: 15px;
                    display: flex;
                    gap: 10px;
                }
                .btn {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: bold;
                    transition: all 0.3s;
                }
                .btn-approve {
                    background: #28a745;
                    color: white;
                }
                .btn-reject {
                    background: #dc3545;
                    color: white;
                }
                .btn:hover {
                    transform: scale(1.05);
                    box-shadow: 0 3px 10px rgba(0,0,0,0.2);
                }
                .btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                #connection-status {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                .connected {
                    background: #28a745;
                    color: white;
                }
                .disconnected {
                    background: #dc3545;
                    color: white;
                }
            </style>
        </head>
        <body>
            <div id="connection-status" class="disconnected">● Connecting...</div>
            
            <div class="container">
                <h1>🛡️ SentinelFlow Fraud Detection Dashboard</h1>
                
                <div class="controls">
                    <button class="kill-switch inactive" id="killSwitchBtn" onclick="toggleKillSwitch()">
                        🛑 ACTIVATE KILL SWITCH
                    </button>
                    <span id="status" class="running">● System Running</span>
                </div>
                
                <div id="alerts"></div>
            </div>
            
            <script>
                let ws = new WebSocket("ws://" + window.location.host + "/ws");
                let killSwitchActive = false;
                
                ws.onopen = function() {
                    updateConnectionStatus(true);
                };
                
                ws.onclose = function() {
                    updateConnectionStatus(false);
                    setTimeout(() => {
                        ws = new WebSocket("ws://" + window.location.host + "/ws");
                    }, 3000);
                };
                
                ws.onmessage = function(event) {
                    const alert = JSON.parse(event.data);
                    displayAlert(alert);
                };
                
                function updateConnectionStatus(connected) {
                    const status = document.getElementById('connection-status');
                    if (connected) {
                        status.textContent = '● Connected';
                        status.className = 'connected';
                    } else {
                        status.textContent = '● Disconnected';
                        status.className = 'disconnected';
                    }
                }
                
                function displayAlert(alert) {
                    const alertsDiv = document.getElementById("alerts");
                    const score = alert.ensemble_decision.final_score;
                    
                    let riskClass = 'low-risk';
                    let riskBadge = 'low';
                    let riskText = 'LOW RISK';
                    
                    if (score > 0.7) {
                        riskClass = 'high-risk';
                        riskBadge = 'high';
                        riskText = 'HIGH RISK';
                    } else if (score > 0.4) {
                        riskClass = 'medium-risk';
                        riskBadge = 'medium';
                        riskText = 'MEDIUM RISK';
                    }
                    
                    const alertHtml = `
                        <div class="alert-card ${riskClass}" id="alert-${alert.alert_id}">
                            <div class="alert-header">
                                <h3>Alert: ${alert.alert_id}</h3>
                                <span class="risk-badge ${riskBadge}">${riskText}</span>
                            </div>
                            
                            <div class="transaction-details">
                                <div class="detail-item">
                                    <div class="detail-label">Transaction ID:</div>
                                    <div>${alert.transaction.transaction_id}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Amount:</div>
                                    <div>${alert.transaction.amount.toFixed(2)}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Customer:</div>
                                    <div>${alert.transaction.customer_id}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Merchant:</div>
                                    <div>${alert.transaction.merchant_id}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Risk Score:</div>
                                    <div><strong>${score.toFixed(3)}</strong></div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">Timestamp:</div>
                                    <div>${new Date(alert.transaction.timestamp).toLocaleString()}</div>
                                </div>
                            </div>
                            
                            <div class="explanation">
                                <strong>🔍 Analysis:</strong><br>
                                ${alert.explanation || 'No explanation available'}
                            </div>
                            
                            <div class="actions">
                                <button class="btn btn-approve" onclick="submitFeedback('${alert.alert_id}', true)">
                                    ✓ Approve (Legitimate)
                                </button>
                                <button class="btn btn-reject" onclick="submitFeedback('${alert.alert_id}', false)">
                                    ✗ Reject (Fraud)
                                </button>
                            </div>
                        </div>
                    `;
                    
                    // Prepend new alerts to top
                    alertsDiv.insertAdjacentHTML('afterbegin', alertHtml);
                    
                    // Keep only last 10 alerts visible
                    const alerts = alertsDiv.children;
                    while (alerts.length > 10) {
                        alertsDiv.removeChild(alerts[alerts.length - 1]);
                    }
                }
                
                async function submitFeedback(alertId, isLegitimate) {
                    try {
                        const response = await fetch(`/feedback/${alertId}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                correct_label: !isLegitimate,  // Invert: true = fraud
                                analyst_notes: ''
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (result.status === 'success') {
                            // Disable buttons
                            const alertCard = document.getElementById(`alert-${alertId}`);
                            const buttons = alertCard.querySelectorAll('.btn');
                            buttons.forEach(btn => {
                                btn.disabled = true;
                                btn.style.opacity = '0.5';
                            });
                            
                            // Add feedback indicator
                            const header = alertCard.querySelector('.alert-header');
                            const indicator = document.createElement('span');
                            indicator.textContent = isLegitimate ? '✓ Approved' : '✗ Rejected';
                            indicator.style.color = isLegitimate ? '#28a745' : '#dc3545';
                            indicator.style.fontWeight = 'bold';
                            header.appendChild(indicator);
                        }
                    } catch (error) {
                        alert('Error submitting feedback: ' + error);
                    }
                }
                
                async function toggleKillSwitch() {
                    try {
                        const action = killSwitchActive ? 'deactivate' : 'activate';
                        const response = await fetch(`/kill-switch/${action}`, {
                            method: 'POST'
                        });
                        
                        const result = await response.json();
                        
                        if (result.status === 'success') {
                            killSwitchActive = result.active;
                            updateKillSwitchUI();
                        }
                    } catch (error) {
                        alert('Error toggling kill switch: ' + error);
                    }
                }
                
                function updateKillSwitchUI() {
                    const btn = document.getElementById('killSwitchBtn');
                    const status = document.getElementById('status');
                    
                    if (killSwitchActive) {
                        btn.textContent = '✅ DEACTIVATE KILL SWITCH';
                        btn.className = 'kill-switch active';
                        status.textContent = '⏸️ System Paused';
                        status.className = 'stopped';
                    } else {
                        btn.textContent = '🛑 ACTIVATE KILL SWITCH';
                        btn.className = 'kill-switch inactive';
                        status.textContent = '● System Running';
                        status.className = 'running';
                    }
                }
            </script>
        </body>
    </html>
    """)