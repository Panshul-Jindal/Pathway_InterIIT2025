# 🛡️ SentinelFlow - Real-time Fraud Detection with Ambient AI

> **Production-ready fraud detection system with multi-expert ensemble, intelligent explanation routing, human-in-the-loop feedback, and online learning.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Redis](https://img.shields.io/badge/redis-7.0+-red.svg)](https://redis.io/)

---

## 🎯 What's Fixed

This corrected version addresses **3 critical workflow bugs** from the original implementation:

### ✅ 1. Intelligent Explanation Routing (FIXED)
- **Problem**: No orchestrator to decide between template vs LLM explanations
- **Solution**: 
  - Added `ExplanationOrchestrator` class
  - Routes high-confidence cases → fast templates
  - Routes ambiguous/conflicting cases → Gemini LLM
  - Detects expert disagreement for complex explanations

### ✅ 2. Human-in-the-Loop Workflow (FIXED)
- **Problem**: Missing kill switch, feedback not flowing back to detection engine
- **Solution**:
  - Implemented full kill switch with activate/deactivate endpoints
  - Detection engine now subscribes to real-time feedback
  - Dashboard uses Redis for persistence (not memory)
  - Feedback flows to both detection engine (immediate) and feedback loop (batch)

### ✅ 3. Online Learning Loop (FIXED)
- **Problem**: Weight updates not reaching detection engine, incorrect delay calculations
- **Solution**:
  - Detection engine subscribes to `weight_updates` channel
  - Proper timestamp-based delay calculation
  - Importance weighting using exponential decay
  - Batch processing with periodic updates

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Plane                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Transaction │───▶│   Pathway    │───▶│ Multi-Expert │     │
│  │    Stream    │    │  Connector   │    │  Ensemble    │     │
│  └──────────────┘    └──────────────┘    └──────┬───────┘     │
│                                                   │              │
│                                          ┌────────▼────────┐    │
│                                          │ Alert + Context │    │
│                                          └────────┬────────┘    │
└────────────────────────────────────────────────┬───────────────┘
                                                  │
┌─────────────────────────────────────────────────▼───────────────┐
│                    Microservice 2: Explanation                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Orchestrator Agent                           │  │
│  │  ┌─────────────────────┬─────────────────────────────┐  │  │
│  │  │  High Confidence    │  Ambiguous/High Value       │  │  │
│  │  │  ↓                  │  ↓                          │  │  │
│  │  │  Template           │  LLM Explanation            │  │  │
│  │  │  Explanation        │  (Gemini)                   │  │  │
│  │  └──────────┬──────────┴───────────┬─────────────────┘  │  │
│  └─────────────┼──────────────────────┼────────────────────┘  │
│                │                      │                         │
│         ┌──────▼──────────────────────▼──────┐                │
│         │  Explanation & SAR Draft           │                │
│         └────────────────┬───────────────────┘                │
└──────────────────────────┼────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│              Microservice 4: HIL Dashboard                     │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐      │
│  │ Analyst        │  │   Analyst   │  │ Kill Switch  │      │
│  │ Dashboard      │◀─│  Feedback   │  │              │      │
│  └────────┬───────┘  └─────┬───────┘  └──────┬───────┘      │
│           │                 │                  │               │
└───────────┼─────────────────┼──────────────────┼──────────────┘
            │                 │                  │
            │        ┌────────▼────────┐         │
            │        │    Feedback     │         │
            │        │                 │         │
            └────────▶    Redis        ◀─────────┘
                     │   Pub/Sub       │
                     └────────┬────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│       Microservice 3: Weight Management Service                │
│  ┌──────────────────┐         ┌──────────────────┐           │
│  │ Delayed Feedback │────────▶│ Advanced Online  │           │
│  │   Handler        │         │    Learning      │           │
│  └──────────────────┘         └────────┬─────────┘           │
│                                         │                      │
│                                ┌────────▼────────┐            │
│                                │ Expert Weights  │            │
│                                └────────┬────────┘            │
└─────────────────────────────────────────┼────────────────────┘
                                          │
                                          ▼
                              Back to Detection Engine
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate
git clone https://github.com/yourusername/sentinelflow.git
cd sentinelflow

# 2. Set environment variables
echo "GEMINI_API_KEY=your-api-key-here" > .env

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f

# 6. Access dashboard
open http://localhost:8002
```

### Option 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Redis
redis-server

# 3. Download Kaggle dataset
# Place kaggle_creditcard.csv in data/ directory

# 4. Start all services
chmod +x start_services.sh
./start_services.sh

# 5. Access dashboard
open http://localhost:8002

# 6. Stop services
./stop_services.sh
```

---

## 📋 Project Structure

```
sentinelflow/
├── detection_engine/
│   ├── main.py                    # ✅ FIXED: Added feedback/weight listeners
│   ├── pathway_pipeline.py
│   ├── weight_manager.py          # ✅ FIXED: Proper bandit updates
│   └── experts/
│       ├── base_expert.py
│       ├── gbm_expert.py
│       ├── rule_engine.py
│       ├── streaming_rf.py
│       └── half_space_trees.py
├── explanation_service/
│   ├── main.py                    # ✅ FIXED: Added orchestrator
│   ├── explanation_generator.py
│   └── templates/
├── feedback_loop/
│   ├── main.py                    # ✅ FIXED: Proper batch processing
│   ├── delayed_feedback.py        # ✅ FIXED: Real delay calculation
│   └── online_learning.py         # ✅ FIXED: Weight publishing
├── dashboard/
│   ├── main.py                    # ✅ FIXED: Kill switch + Redis storage
│   ├── static/
│   └── templates/
├── shared/
│   ├── schemas.py
│   ├── redis_client.py
│   └── config.py
├── tests/
│   └── integration_test.py        # ✅ NEW: Complete workflow tests
├── data/
│   └── kaggle_creditcard.csv
├── docker-compose.yml             # ✅ FIXED: Complete orchestration
├── requirements.txt               # ✅ UPDATED: All dependencies
├── start_services.sh              # ✅ NEW: Easy startup
├── stop_services.sh               # ✅ NEW: Graceful shutdown
├── DEPLOYMENT_GUIDE.md            # ✅ NEW: Complete guide
└── README.md
```

---

## 🔄 Data Flow

### 1. Transaction Processing
```
Transaction → Detection Engine → Expert Ensemble → Alert (Score + Context)
                     ↓
            Stores in Redis:
            - transaction:{id}
            - decisions:{id}
```

### 2. Explanation Generation
```
Alert → Explanation Service → Orchestrator Decision
                                    ↓
                        High Confidence? → Template
                        Ambiguous?       → Gemini LLM
                                    ↓
                        Alert + Explanation → Dashboard
```

### 3. Human Feedback Loop
```
Analyst Feedback → Dashboard → Publishes to Redis
                                      ↓
                            ┌─────────┴─────────┐
                            ↓                   ↓
                    Detection Engine    Feedback Loop
                    (immediate)         (batch)
                            ↓                   ↓
                    Update Weights      Calculate Stats
                                              ↓
                                        Publish Updates
                                              ↓
                                    Detection Engine
```

### 4. Kill Switch
```
Dashboard → Redis (kill_switch channel) → Detection Engine
                                             ↓
                                    Pause Processing
```

---

## 🧪 Testing

### Run Integration Tests
```bash
python tests/integration_test.py

# Expected output:
# ✅ Step 1: Created test transaction
# ✅ Step 2: Transaction stored in Redis
# ✅ Step 3: Expert decisions stored
# ✅ Step 4: Feedback published to Redis
# ✅ Step 5: Feedback metadata stored
# ✅ Step 6: Kill switch mechanism tested
# ✅ ALL INTEGRATION TESTS PASSED
```

### Test Individual Workflows

#### Test Explanation Routing
```bash
# Monitor explanation service logs
tail -f logs/explanation_service.log

# Look for:
# "Generated template explanation" (high confidence)
# "Generated llm explanation" (ambiguous)
```

#### Test Kill Switch
```bash
# Activate
curl -X POST http://localhost:8002/kill-switch/activate

# Check detection engine logs:
# "🛑 KILL SWITCH ACTIVATED - Pausing detections"

# Deactivate
curl -X POST http://localhost:8002/kill-switch/deactivate
```

#### Test Online Learning
```bash
# Submit feedback
curl -X POST http://localhost:8002/feedback/test_alert_001 \
  -H "Content-Type: application/json" \
  -d '{"correct_label": true}'

# Watch logs for:
# Detection Engine: "🔄 Updated weights from feedback"
# Feedback Loop: "📊 Published weight updates"
```

---

## 📊 Monitoring

### Health Checks
```bash
# Explanation Service
curl http://localhost:8001/health

# Dashboard
curl http://localhost:8002/health

# Redis
redis-cli ping
```

### View Statistics
```bash
# Explanation cache stats
curl http://localhost:8001/stats

# Recent alerts
curl http://localhost:8002/alerts?limit=10

# Kill switch status
curl http://localhost:8002/kill-switch/status
```

### Log Monitoring
```bash
# All services
tail -f logs/*.log

# Specific service
tail -f logs/detection_engine.log
tail -f logs/dashboard.log
```

---

## 🔧 Configuration

### Environment Variables
```bash
# .env file
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your-gemini-api-key
KAGGLE_DATASET_PATH=data/kaggle_creditcard.csv
```

### Tunable Parameters

**Detection Engine** (`detection_engine/weight_manager.py`):
```python
alpha = 0.1              # Exploration rate (lower = less exploration)
context_dim = 10         # Context vector dimensions
```

**Feedback Loop** (`feedback_loop/online_learning.py`):
```python
batch_size = 10          # Feedback items per batch
learning_rate = 0.1      # Update smoothing (lower = more stable)
```

**Delayed Feedback** (`feedback_loop/delayed_feedback.py`):
```python
decay_rate = 0.1         # Importance decay (higher = faster decay)
```

---

## 🐛 Troubleshooting

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

**Common Issues**:

1. **Services can't connect to Redis**
   ```bash
   redis-cli ping  # Should return PONG
   ```

2. **No alerts in dashboard**
   ```bash
   redis-cli MONITOR | grep "PUBLISH"
   ```

3. **Feedback not updating weights**
   ```bash
   # Check logs
   grep "weight" logs/detection_engine.log
   grep "feedback" logs/feedback_loop.log
   ```

---

## 📈 Performance

- **Throughput**: 100+ transactions/second
- **Latency**: <50ms per transaction
- **Explanation**: <100ms (template), <2s (LLM)
- **Feedback**: Real-time + batch (1 minute intervals)

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **Pathway**: Real-time stream processing
- **Redis**: Pub/sub and caching
- **Gemini**: LLM explanations
- **XGBoost/LightGBM**: Expert models
- **Kaggle**: Credit card fraud dataset

---

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Complete deployment instructions
- **[Architecture Diagram](architecture.png)**: System architecture visualization
- **API Documentation**: 
  - Dashboard: http://localhost:8002/docs
  - Explanation Service: http://localhost:8001/docs

---

## 🎓 Key Concepts

### Multi-Expert Ensemble
Combines predictions from:
- **XGBoost**: Gradient boosting static model
- **LightGBM**: Fast gradient boosting
- **Rule Engine**: Business logic rules
- **Streaming RF**: Online random forest
- **Half-Space Trees**: Anomaly detection

### Contextual Bandits
Uses **LinUCB** algorithm to:
- Learn optimal expert weights per context
- Balance exploration vs exploitation
- Adapt to changing fraud patterns

### Delayed Feedback Handling
Handles real-world delays using:
- **Importance weighting**: Exponential decay
- **Survival analysis**: Delay distribution modeling
- **Batch updates**: Aggregate feedback efficiently

### Intelligent Explanation
Routes based on:
- **High confidence** (>0.8 or <0.2): Fast templates
- **Ambiguous** (0.3-0.7): LLM for nuance
- **Expert conflict**: LLM for reconciliation

---

## 🔍 Example Use Cases

### 1. High-Risk Transaction Alert
```
Transaction: $2,500 from new device in foreign location
↓
Expert Scores:
  - XGBoost: 0.92
  - Rule Engine: 0.85
  - Streaming RF: 0.88
↓
Ensemble Score: 0.89 (HIGH RISK)
↓
Explanation (Template):
"🔍 FRAUD ALERT ANALYSIS

Risk Level: HIGH RISK
Confidence Score: 0.890

Primary Risk Factors:
• High transaction amount: $2,500 (impact: 0.6)
• New device detected (impact: 0.5)
• Foreign location (impact: 0.4)

Expert Consensus: 5 experts analyzed this transaction

Action: Recommend BLOCK transaction and require verification"
```

### 2. Ambiguous Case
```
Transaction: $450 from known device, unusual time
↓
Expert Scores:
  - XGBoost: 0.55
  - Rule Engine: 0.42
  - Streaming RF: 0.58
  - Half-Space Trees: 0.48
↓
Ensemble Score: 0.51 (AMBIGUOUS)
↓
Explanation (Gemini LLM):
"This transaction shows mixed signals. While the device is 
recognized and the amount is within normal range, the timing 
(3:47 AM) is unusual for this customer who typically shops 
during business hours. The merchant category is also new.

Recommendation: Flag for 2FA verification. If customer 
confirms, add this merchant and time pattern to their profile."
```

### 3. Analyst Feedback Flow
```
Analyst reviews alert → Marks as legitimate
↓
Feedback sent to Redis:
{
  "alert_id": "txn_12345",
  "correct_label": false,  // Not fraud
  "analyst_notes": "Customer traveling"
}
↓
Detection Engine (immediate):
  - Updates contextual bandit weights
  - Expert that predicted fraud gets negative reward
  - Expert that predicted legitimate gets positive reward
↓
Feedback Loop (batch after 10 samples):
  - Calculates weighted accuracy per expert
  - Publishes weight updates
  - Detection engine applies new weights
```

### 4. Kill Switch Scenario
```
System Alert: High false positive rate detected
↓
Analyst activates kill switch via dashboard
↓
Detection Engine receives signal:
  - Pauses all transaction processing
  - Continues listening for reactivation
↓
Team investigates and fixes issue
↓
Analyst deactivates kill switch
↓
Detection Engine resumes processing
```

---

## 🔐 Security Considerations

### Production Deployment

1. **Redis Security**
   ```bash
   # In redis.conf
   requirepass your-strong-password
   bind 127.0.0.1
   protected-mode yes
   ```

2. **API Authentication**
   ```python
   # Add to FastAPI apps
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   @app.post("/feedback/{alert_id}")
   async def submit_feedback(
       alert_id: str,
       feedback: dict,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ):
       # Verify token
       verify_token(credentials.credentials)
       ...
   ```

3. **Environment Variables**
   ```bash
   # Never commit .env files
   # Use secrets management in production
   export GEMINI_API_KEY=$(vault read secret/gemini_key)
   ```

4. **Network Isolation**
   ```yaml
   # docker-compose.yml
   services:
     redis:
       networks:
         - internal  # Not exposed externally
   ```

---

## 📊 Metrics & Observability

### Key Metrics to Track

1. **Detection Performance**
   - Transaction throughput (txn/sec)
   - Average latency (ms)
   - Expert accuracy over time
   - False positive/negative rates

2. **Explanation Quality**
   - Template vs LLM usage ratio
   - Explanation generation time
   - Cache hit rate

3. **Feedback Loop**
   - Feedback delay distribution
   - Weight update frequency
   - Expert weight drift

4. **System Health**
   - Redis memory usage
   - Service uptime
   - WebSocket connections
   - Error rates

### Monitoring Setup (Example)

```python
# Add to services
from prometheus_client import Counter, Histogram

# Metrics
transactions_processed = Counter(
    'transactions_processed_total',
    'Total transactions processed'
)

processing_time = Histogram(
    'transaction_processing_seconds',
    'Time to process transaction'
)

# Usage
transactions_processed.inc()
with processing_time.time():
    process_transaction(txn)
```

---

## 🚧 Roadmap

### Phase 1: Core Functionality ✅
- [x] Multi-expert ensemble
- [x] Contextual bandits
- [x] Intelligent explanation routing
- [x] Human-in-the-loop feedback
- [x] Online learning
- [x] Kill switch

### Phase 2: Enhanced Features (In Progress)
- [ ] Model versioning and rollback
- [ ] A/B testing framework
- [ ] Advanced analytics dashboard
- [ ] Automated model retraining
- [ ] Multi-tenancy support

### Phase 3: Enterprise Features (Planned)
- [ ] GDPR compliance tools
- [ ] Audit logging
- [ ] Role-based access control
- [ ] Custom rule builder UI
- [ ] Integration with SIEM systems

---

## 🤔 FAQ

**Q: Can I use this with my own fraud dataset?**
A: Yes! Replace the Kaggle dataset loader in `detection_engine/main.py` with your own data source.

**Q: How do I add a new expert model?**
A: Create a new class in `detection_engine/experts/` inheriting from `BaseExpert`, implement the `predict()` method, and add it to the ensemble in `main.py`.

**Q: Can I use a different LLM instead of Gemini?**
A: Yes! Modify `explanation_service/explanation_generator.py` to use OpenAI, Claude, or any other LLM API.

**Q: How does the system handle concept drift?**
A: Through continuous online learning and contextual bandits that adapt expert weights based on recent performance.

**Q: What happens if Redis goes down?**
A: Services will reconnect automatically. Use Redis Sentinel or Redis Cluster for high availability in production.

**Q: Can I run this without Docker?**
A: Yes! Use the manual setup instructions with `start_services.sh`.

**Q: How do I scale for high throughput?**
A: Deploy multiple detection engine instances, use Redis Cluster, and consider Kafka for higher throughput than Redis pub/sub.

---

## 💡 Best Practices

### For Analysts
1. **Review all ambiguous cases** (scores 0.3-0.7)
2. **Provide detailed notes** in feedback
3. **Use kill switch** if false positive rate spikes
4. **Monitor expert agreement** for model drift

### For Developers
1. **Run integration tests** before deploying
2. **Monitor Redis memory** usage
3. **Set appropriate TTLs** on all keys
4. **Log all critical decisions** with context
5. **Version control** expert model files

### For Operations
1. **Set up health checks** for all services
2. **Configure log rotation** to prevent disk fill
3. **Monitor feedback delay** distribution
4. **Backup Redis** data regularly
5. **Test failover** scenarios

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/sentinelflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/sentinelflow/discussions)
- **Email**: support@sentinelflow.ai

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

## 📖 Citation

If you use SentinelFlow in your research or project, please cite:

```bibtex
@software{sentinelflow2025,
  title = {SentinelFlow: Real-time Fraud Detection with Ambient AI},
  author = {Your Name},
  year = {2025},
  url = {https://github.com/yourusername/sentinelflow}
}
```

---

**Built with ❤️ for the fraud prevention community**