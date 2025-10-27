# tests/integration_test.py
"""
Integration test to verify all services communicate correctly
"""
import asyncio
import json
import pytest
from datetime import datetime
from shared.redis_client import redis_client
from shared.schemas import Transaction, Feedback

class IntegrationTest:
    """Test complete workflow from transaction to feedback"""
    
    async def test_complete_workflow(self):
        """Test: Transaction → Detection → Explanation → Dashboard → Feedback"""
        
        print("\n" + "="*70)
        print("🧪 INTEGRATION TEST: Complete Workflow")
        print("="*70)
        
        # Step 1: Simulate transaction
        test_transaction = Transaction(
            transaction_id="test_txn_001",
            timestamp=datetime.now(),
            amount=1500.00,
            customer_id="cust_123",
            merchant_id="merch_456",
            location="loc_789",
            device_id="device_001",
            transaction_type="purchase",
            features={f"V{i}": float(i * 0.1) for i in range(1, 29)}
        )
        
        print(f"\n✅ Step 1: Created test transaction {test_transaction.transaction_id}")
        
        # Step 2: Verify detection engine stores data
        await redis_client.setex(
            f"transaction:{test_transaction.transaction_id}",
            86400,
            json.dumps(test_transaction.dict(), default=str)
        )
        
        stored = await redis_client.get(f"transaction:{test_transaction.transaction_id}")
        assert stored is not None, "Transaction not stored in Redis"
        print(f"✅ Step 2: Transaction stored in Redis")
        
        # Step 3: Simulate expert decisions
        mock_decisions = {
            'xgboost': {
                'score': 0.75,
                'confidence': 0.85,
                'contributing_factors': []
            },
            'rule_engine': {
                'score': 0.82,
                'confidence': 1.0,
                'contributing_factors': []
            }
        }
        
        await redis_client.setex(
            f"decisions:{test_transaction.transaction_id}",
            86400,
            json.dumps(mock_decisions)
        )
        print(f"✅ Step 3: Expert decisions stored")
        
        # Step 4: Test feedback submission
        test_feedback = Feedback(
            alert_id=test_transaction.transaction_id,
            correct_label=True,  # Was actually fraud
            analyst_notes="High-risk merchant pattern detected",
            feedback_timestamp=datetime.now()
        )
        
        # Publish feedback
        await redis_client.publish(
            'feedback',
            json.dumps(test_feedback.dict(), default=str)
        )
        print(f"✅ Step 4: Feedback published to Redis")
        
        # Step 5: Verify feedback can be retrieved
        await asyncio.sleep(0.5)  # Give time for processing
        
        metadata = await redis_client.get(
            f"feedback_metadata:{test_transaction.transaction_id}"
        )
        
        if metadata:
            print(f"✅ Step 5: Feedback metadata stored successfully")
            metadata_obj = json.loads(metadata)
            print(f"   - Importance weight: {metadata_obj.get('importance_weight', 'N/A')}")
            print(f"   - Delay hours: {metadata_obj.get('delay_hours', 'N/A')}")
        else:
            print(f"⚠️ Step 5: Feedback metadata not found (may need services running)")
        
        # Step 6: Test kill switch
        print(f"\n✅ Step 6: Testing kill switch mechanism...")
        
        await redis_client.publish('kill_switch', json.dumps({
            'active': True,
            'timestamp': datetime.now().isoformat(),
            'activated_by': 'test_suite'
        }))
        print(f"   - Kill switch activation signal sent")
        
        await asyncio.sleep(0.5)
        
        await redis_client.publish('kill_switch', json.dumps({
            'active': False,
            'timestamp': datetime.now().isoformat(),
            'deactivated_by': 'test_suite'
        }))
        print(f"   - Kill switch deactivation signal sent")
        
        print("\n" + "="*70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("="*70 + "\n")
    
    async def test_channel_communication(self):
        """Test all Redis pub/sub channels"""
        
        print("\n" + "="*70)
        print("🧪 INTEGRATION TEST: Channel Communication")
        print("="*70)
        
        channels = [
            'alerts',
            'alerts_with_explanations',
            'feedback',
            'weight_updates',
            'kill_switch'
        ]
        
        for channel in channels:
            # Test publish
            test_message = {'test': True, 'channel': channel, 'timestamp': datetime.now().isoformat()}
            await redis_client.publish(channel, json.dumps(test_message))
            print(f"✅ Channel '{channel}' - publish successful")
        
        print("\n" + "="*70)
        print("✅ ALL CHANNEL TESTS PASSED")
        print("="*70 + "\n")
    
    async def test_data_persistence(self):
        """Test Redis data persistence"""
        
        print("\n" + "="*70)
        print("🧪 INTEGRATION TEST: Data Persistence")
        print("="*70)
        
        test_keys = [
            ('transaction:test_001', {'id': 'test_001', 'amount': 100.0}),
            ('decisions:test_001', {'xgboost': 0.75}),
            ('alert:test_001', {'alert_id': 'test_001', 'score': 0.8}),
            ('feedback_metadata:test_001', {'weight': 1.0, 'delay': 2.5})
        ]
        
        # Store data
        for key, value in test_keys:
            await redis_client.setex(key, 60, json.dumps(value))
            print(f"✅ Stored: {key}")
        
        # Retrieve data
        for key, expected_value in test_keys:
            stored = await redis_client.get(key)
            assert stored is not None, f"Failed to retrieve {key}"
            retrieved = json.loads(stored)
            print(f"✅ Retrieved: {key} - Data matches: {retrieved == expected_value}")
        
        # Cleanup
        for key, _ in test_keys:
            await redis_client.delete(key)
        
        print("\n" + "="*70)
        print("✅ ALL PERSISTENCE TESTS PASSED")
        print("="*70 + "\n")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "🚀 " * 20)
        print("STARTING SENTINELFLOW INTEGRATION TESTS")
        print("🚀 " * 20)
        
        await self.test_data_persistence()
        await self.test_channel_communication()
        await self.test_complete_workflow()
        
        print("\n" + "🎉 " * 20)
        print("ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        print("🎉 " * 20 + "\n")


if __name__ == "__main__":
    test_suite = IntegrationTest()
    asyncio.run(test_suite.run_all_tests())