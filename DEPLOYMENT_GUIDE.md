# SentinelFlow Deployment Guide

## 🔧 Critical Fixes Applied

### 1. **Intelligent Explanation Routing** ✅
- **Added**: `ExplanationOrchestrator` class in `explanation_service/main.py`
- **Routes**: High confidence → Template | Ambiguous → LLM
- **Checks**: Expert conflict detection for complex cases

### 2. **Human-in-the-Loop Workflow** ✅
- **Kill Switch**: Implemented in `dashboard/main.py`
  - `/kill-switch/activate` endpoint
  - `/kill-switch/deactivate` endpoint
  - Broadcasts to detection engine via Redis pub/sub
- **Real-time Feedback**: Detection engine now subscribes to `feedback` channel
- **Persistence**: Alerts stored in Redis instead of memory

### 3. **Online Learning Loop** ✅
- **Feedback Flow**: Dashboard → Detection Engine (immediate) + Feedback Loop (batch)
- **Weight Updates**: Detection engine subscribes to `weight_updates` channel
- **Delay Handling**: Proper timestamp comparison and importance weighting
- **Batch Processing**: Accumulates feedback and updates periodically

---

## 📋 Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn pathway-ai redis xgboost lightgbm numpy pandas google-generativeai

# Start Redis
docker run -d -p 6379:6379 redis:latest
# OR
redis-server
```

---

## 🚀 Service Startup Order

### 1. Start Redis
```bash
# Docker
docker run -d -p 6379:6379 --name sentinelflow-redis redis:latest

# Or local Redis
redis-server
```

### 2. Start Detection Engine
```bash
cd detection_engine
python main.py

# Expected output:
# 🚀 Starting Detection Engine...
# 📊 Transaction processing started
# 👂 Listening for analyst feedback...
# 👂 Listening for weight updates...
# 👂 Listening for kill switch...
```

### 3. Start Explanation Service
```bash
cd explanation_service
export GEMINI_API_KEY="your-gemini-api-key"  # Optional for LLM explanations
python main.py

# Expected output:
# 🎯 Explanation Service started - listening for alerts...
```

### 4. Start Dashboard
```bash
cd dashboard
python main.py

# Expected output:
# 📊 Dashboard started - listening for alerts with explanations...
# Open browser: http://localhost:8002
```

### 5. Start Feedback Loop
```bash
cd feedback_loop
python main.py

# Expected output:
# 🔄 Starting Feedback Loop Service...
# 👂 Feedback Loop listening for analyst feedback...
```

---

## 🔄 Data Flow Verification

### Complete Workflow Test

```python
# Run integration tests
python tests/integration_test.py

# Should see:
# ✅ Step 1: Created test transaction
# ✅ Step 2: Transaction stored in Redis
# ✅ Step 3: Expert decisions stored
# ✅ Step 4: Feedback published to Redis
# ✅ Step 5: Feedback metadata stored
# ✅ Step 6: Kill switch mechanism tested
```

### Manual Channel Test

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Test alerts channel
r.publish('alerts', json.dumps({
    'transaction': {'transaction_id': 'test_001'},
    'ensemble_decision': {'final_score': 0.85}
}))

# Check if explanation service receives it
# Then check if dashboard receives explained alert
```

---

## 📊 Monitoring Endpoints

### Detection Engine
```bash
# No HTTP endpoints - check logs
tail -f detection_engine.log
```

### Explanation Service
```bash
curl http://localhost:8001/health
# Response: {"status": "healthy", "cache_size": 10}

curl http://localhost:8001/stats
# Response: {"cache_size": 10, "cache_keys": [...]}
```

### Dashboard
```bash
curl http://localhost:8002/health
# Response: {
#   "status": "healthy",
#   "websocket_connections": 2,
#   "kill_switch": {"active": false}
# }

curl http://localhost:8002/kill-switch/status
# Response: {"active": false, "activation_time": null}

curl http://localhost:8002/alerts
# Response: {"status": "success", "count": 10, "alerts": [...]}
```

---

## 🔐 Redis Key Structure

```
# Transactions (24h TTL)
transaction:{transaction_id} → Transaction JSON

# Expert Decisions (24h TTL)
decisions:{transaction_id} → Dict of expert decisions

# Alerts (24h TTL)
alert:{alert_id} → Alert JSON

# Feedback Metadata (24h TTL)
feedback_metadata:{alert_id} → Feedback with importance weights

# Explanations (24h TTL)
explanation:{transaction_id} → Explanation JSON

# Statistics (1h TTL)
online_learning_stats → Performance metrics
```

---

## 📡 Redis Pub/Sub Channels

| Channel | Publisher | Subscriber | Purpose |
|---------|-----------|------------|---------|
| `alerts` | Detection Engine | Explanation Service | Raw alerts |
| `alerts_with_explanations` | Explanation Service | Dashboard | Explained alerts |
| `feedback` | Dashboard | Detection Engine + Feedback Loop | Analyst feedback |
| `weight_updates` | Feedback Loop | Detection Engine | Batch weight updates |
| `kill_switch` | Dashboard | Detection Engine | Emergency stop |

---

## 🧪 Testing Workflows

### 1. Test Intelligent Explanation Routing

```python
# High confidence case (should use template)
alert = {
    'ensemble_decision': {
        'final_score': 0.95,  # High score
        'expert_decisions': {...}
    }
}
# Check logs: "Generated template explanation"

# Ambiguous case (should use LLM)
alert = {
    'ensemble_decision': {
        'final_score': 0.55,  # Medium score
        'expert_decisions': {...}
    }
}
# Check logs: "Generated llm explanation"
```

### 2. Test Human-in-the-Loop

```bash
# Activate kill switch
curl -X POST http://localhost:8002/kill-switch/activate

# Check detection engine logs:
# "🛑 KILL SWITCH ACTIVATED - Pausing detections"

# Deactivate
curl -X POST http://localhost:8002/kill-switch/deactivate

# Check logs:
# "✅ Kill switch deactivated - Resuming detections"
```

### 3. Test Online Learning Loop

```bash
# Submit feedback via dashboard
curl -X POST http://localhost:8002/feedback/test_alert_001 \
  -H "Content-Type: application/json" \
  -d '{"correct_label": true, "analyst_notes": "Clear fraud pattern"}'

# Check feedback_loop logs:
# "📊 Processed feedback for alert test_alert_001"
# "🔄 Processing batch of 10 feedback samples"
# "📊 Published weight updates: {'xgboost': 0.85, ...}"

# Check detection_engine logs:
# "🔄 Applied weight updates: {'xgboost': 0.85, ...}"
```

---

## 🐛 Troubleshooting

### Issue: Services can't connect to Redis
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check Redis URL in services
echo $REDIS_URL
# Should be: redis://localhost:6379
```

### Issue: No alerts appearing in dashboard
```bash
# Check if detection engine is publishing
redis-cli MONITOR | grep "PUBLISH alerts"

# Check if explanation service is subscribing
# Look for log: "🎯 Explanation Service started"

# Check if dashboard is subscribing
# Look for log: "📊 Dashboard started"
```

### Issue: Feedback not updating weights
```bash
# Check feedback is being published
redis-cli MONITOR | grep "PUBLISH feedback"

# Check detection engine is subscribed
# Look for log: "👂 Listening for analyst feedback..."

# Check feedback loop is processing
# Look for log: "📊 Processed feedback for alert..."
```

### Issue: Kill switch not working
```bash
# Test kill switch channel
redis-cli
> PUBLISH kill_switch '{"active":true}'

# Check detection engine response
# Should see: "🛑 KILL SWITCH ACTIVATED"
```

---

## 📈 Performance Tuning

### Batch Sizes
```python
# feedback_loop/main.py
self.buffer_size = 10  # Increase for less frequent updates

# feedback_loop/online_learning.py
self.batch_size = 10  # Increase for more stable updates
```

### Learning Rates
```python
# detection_engine/weight_manager.py
alpha = 0.1  # Lower = less exploration

# feedback_loop/online_learning.py
self.learning_rate = 0.1  # Lower = more stable updates
```

### Importance Weighting
```python
# feedback_loop/delayed_feedback.py
decay_rate = 0.1  # Higher = faster decay for old feedback
```

---

## 🔒 Production Checklist

- [ ] Set strong Redis password
- [ ] Enable Redis persistence (AOF or RDB)
- [ ] Set up proper TTLs for all keys
- [ ] Configure Gemini API key for explanation service
- [ ] Set up monitoring and alerting
- [ ] Configure proper logging (file rotation)
- [ ] Set up backup for Redis data
- [ ] Test all failure scenarios
- [ ] Load test with production traffic
- [ ] Set up health check monitoring

---

## 📝 Environment Variables

```bash
# .env file
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your-api-key-here
KAGGLE_DATASET_PATH=data/kaggle_creditcard.csv
DETECTION_ENGINE_URL=http://localhost:8000
EXPLANATION_SERVICE_URL=http://localhost:8001
DASHBOARD_URL=http://localhost:8002
```

---

## 🎯 Success Criteria

System is working correctly when:

1. ✅ Transactions flow through detection engine
2. ✅ Alerts receive explanations (template or LLM)
3. ✅ Dashboard displays alerts in real-time
4. ✅ Analyst feedback updates weights immediately
5. ✅ Batch updates process every minute
6. ✅ Kill switch stops/resumes detection
7. ✅ All data persists in Redis
8. ✅ Integration tests pass

---

## 📚 Additional Resources

- [Pathway Documentation](https://pathway.com/developers/documentation)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Pub/Sub Guide](https://redis.io/docs/manual/pubsub/)
- [Contextual Bandits Paper](https://arxiv.org/abs/1003.0146)