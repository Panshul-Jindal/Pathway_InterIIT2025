#!/bin/bash

# Create root directory
mkdir -p sentinelflow

# Navigate into it
cd sentinelflow || exit

# Create top-level files
touch docker-compose.yml README.md requirements.txt

# -------------------------------
# Data directory
# -------------------------------
mkdir -p data
touch data/kaggle_creditcard.csv

# -------------------------------
# Detection engine
# -------------------------------
mkdir -p detection_engine/experts
touch detection_engine/main.py
touch detection_engine/pathway_pipeline.py
touch detection_engine/weight_manager.py
touch detection_engine/experts/__init__.py
touch detection_engine/experts/base_expert.py
touch detection_engine/experts/gbm_expert.py
touch detection_engine/experts/rule_engine.py
touch detection_engine/experts/streaming_rf.py
touch detection_engine/experts/half_space_trees.py

# -------------------------------
# Explanation service
# -------------------------------
mkdir -p explanation_service/templates
touch explanation_service/main.py
touch explanation_service/explanation_generator.py

# -------------------------------
# Feedback loop
# -------------------------------
mkdir -p feedback_loop
touch feedback_loop/main.py
touch feedback_loop/delayed_feedback.py
touch feedback_loop/online_learning.py

# -------------------------------
# Dashboard
# -------------------------------
mkdir -p dashboard/static
mkdir -p dashboard/templates
touch dashboard/main.py

# -------------------------------
# Shared utilities
# -------------------------------
mkdir -p shared
touch shared/schemas.py
touch shared/redis_client.py
touch shared/config.py

echo "✅ sentinelflow project structure created successfully."
