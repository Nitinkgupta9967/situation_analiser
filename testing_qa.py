"""
Comprehensive Testing and Quality Assurance for Legal Situation Analyzer
"""
import unittest
import sqlite3
import tempfile
import os
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import requests
from datetime import datetime, timedelta

# Import application modules
sys.path.append('.')
try:
    from legal_analyzer import LegalSituationAnalyzer
    from config_database import DatabaseManager, LegalKnowledgeBase, SessionManager
    from advanced_models import LegalModel
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are in the same directory")

class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.db_manager = DatabaseManager(self.test_db_path)
        
    def tearDown(self):
        """Clean up test database"""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
    def test_database_initialization(self):
        """Test database tables are created correctly"""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Check if all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['sessions', 'legal_knowledge', 'case_analyses']
        for table in expected_tables:
            self.assertIn(table, tables)
            
        conn.close()
        
    def test_session_creation(self):
        """Test creating a new session"""
        session_id = self.db_manager.create_session()
        self.assertIsNotNone(session_id)
        self.assertIsInstance(session_id, str)
        
    def test_save_and_retrieve_analysis(self):
        """Test saving and retrieving analysis results"""
        session_id = self.db_manager.create_session()
        test_analysis = {
            'jurisdiction': 'California',
            'case_type': 'Contract Dispute',
            'risk_score': 7.5,
            'recommendations': ['Seek legal counsel', 'Gather documentation']
        }
        
        # Save analysis
        analysis_id = self.db_manager.save_analysis(session_id, test_analysis)
        self.assertIsNotNone(analysis_id)
        
        # Retrieve analysis
        retrieved = self.db_manager.get_analysis(analysis_id)
        self.assertEqual(retrieved['jurisdiction'], 'California')
        self.assertEqual(retrieved['risk_score'], 7.5)

class TestLegalKnowledgeBase(unittest.TestCase):
    """Test cases for LegalKnowledgeBase class"""
    
    def setUp(self):
        """Set up test knowledge base"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.kb = LegalKnowledgeBase(self.test_db_path)
        
    def tearDown(self):
        """Clean up test database"""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
    def test_add_legal_concept(self):
        """Test adding legal concepts to knowledge base"""
        concept = {
            'term': 'Contract',
            'definition': 'A legally binding agreement between parties',
            'category': 'Civil Law',
            'related_terms': ['Agreement', 'Covenant', 'Compact']
        }
        
        concept_id = self.kb.add_concept(concept)
        self.assertIsNotNone(concept_id)
        
        # Retrieve and verify
        retrieved = self.kb.get_concept('Contract')
        self.assertEqual(retrieved['definition'], concept['definition'])
        
    def test_search_concepts(self):
        """Test searching legal concepts"""
        # Add test data
        concepts = [
            {'term': 'Tort', 'category': 'Civil Law'},
            {'term': 'Negligence', 'category': 'Tort Law'},
            {'term': 'Contract', 'category': 'Civil Law'}
        ]
        
        for concept in concepts:
            self.kb.add_concept(concept)
            
        # Search by category
        civil_concepts = self.kb.search_by_category('Civil Law')
        self.assertEqual(len(civil_concepts), 2)

class TestLegalSituationAnalyzer(unittest.TestCase):
    """Test cases for LegalSituationAnalyzer class"""
    
    def setUp(self):
        """Set up test analyzer"""
        self.analyzer = LegalSituationAnalyzer()
        
    @patch('legal_analyzer.LegalModel')
    def test_analyze_situation(self, mock_model):
        """Test situation analysis functionality"""
        # Mock model predictions
        mock_model_instance = Mock()
        mock_model_instance.predict.return_value = {
            'case_type': 'Personal Injury',
            'confidence': 0.85,
            'risk_assessment': 'Medium',
            'recommended_actions': ['Document injuries', 'Seek medical attention']
        }
        mock_model.return_value = mock_model_instance
        
        # Test input
        situation = {
            'description': 'Slip and fall accident at grocery store',
            'date': '2024-01-15',
            'injuries': 'Broken wrist',
            'witnesses': 2
        }
        
        # Analyze
        result = self.analyzer.analyze(situation)
        
        # Verify results
        self.assertIn('case_type', result)
        self.assertEqual(result['case_type'], 'Personal Injury')
        self.assertIn('risk_assessment', result)
        
    def test_jurisdiction_detection(self):
        """Test jurisdiction detection from text"""
        test_cases = [
            ('This happened in California', 'California'),
            ('I live in New York City', 'New York'),
            ('The incident occurred in Texas', 'Texas')
        ]
        
        for text, expected_jurisdiction in test_cases:
            result = self.analyzer.detect_jurisdiction(text)
            self.assertEqual(result, expected_jurisdiction)
            
    def test_statute_of_limitations_check(self):
        """Test statute of limitations calculation"""
        # Test case within limitations
        recent_date = datetime.now() - timedelta(days=180)
        result = self.analyzer.check_statute_of_limitations(
            'Personal Injury',
            'California',
            recent_date.isoformat()
        )
        self.assertTrue(result['within_limitations'])
        
        # Test case outside limitations
        old_date = datetime.now() - timedelta(days=1095)  # 3 years
        result = self.analyzer.check_statute_of_limitations(
            'Personal Injury',
            'California',
            old_date.isoformat()
        )
        self.assertFalse(result['within_limitations'])

class TestAdvancedModels(unittest.TestCase):
    """Test cases for AI/ML models"""
    
    def setUp(self):
        """Set up test models"""
        self.model = LegalModel()
        
    def test_model_initialization(self):
        """Test model loads correctly"""
        self.assertIsNotNone(self.model)
        self.assertTrue(hasattr(self.model, 'predict'))
        
    def test_model_prediction(self):
        """Test model makes predictions"""
        test_input = {
            'text': 'Contract dispute over unpaid services',
            'amount': 5000,
            'duration': '6 months'
        }
        
        prediction = self.model.predict(test_input)
        
        # Verify prediction structure
        self.assertIsInstance(prediction, dict)
        self.assertIn('case_type', prediction)
        self.assertIn('confidence', prediction)
        self.assertGreaterEqual(prediction['confidence'], 0)
        self.assertLessEqual(prediction['confidence'], 1)

class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager"""
    
    def setUp(self):
        """Set up test session manager"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.session_manager = SessionManager(self.test_db_path)
        
    def tearDown(self):
        """Clean up"""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
    def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        # Create session
        session = self.session_manager.create_session()
        self.assertIsNotNone(session['id'])
        self.assertEqual(session['status'], 'active')
        
        # Update session
        self.session_manager.update_session(session['id'], {'status': 'completed'})
        
        # Retrieve and verify
        updated = self.session_manager.get_session(session['id'])
        self.assertEqual(updated['status'], 'completed')
        
    def test_session_expiration(self):
        """Test session expiration handling"""
        # Create session with short expiration
        session = self.session_manager.create_session(expire_minutes=1)
        
        # Mock time passage
        with patch('time.time', return_value=time.time() + 120):
            is_valid = self.session_manager.is_session_valid(session['id'])
            self.assertFalse(is_valid)

class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.analyzer = LegalSituationAnalyzer(db_path=self.test_db_path)
        
    def tearDown(self):
        """Clean up"""
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)
        
    def test_complete_analysis_workflow(self):
        """Test complete analysis from input to output"""
        # Create session
        session_id = self.analyzer.create_session()
        
        # Input legal situation
        situation = {
            'description': 'Employment discrimination based on age',
            'date': '2024-01-01',
            'location': 'California',
            'damages': 'Lost wages and emotional distress'
        }
        
        # Perform analysis
        analysis = self.analyzer.analyze_situation(session_id, situation)
        
        # Verify comprehensive results
        self.assertIn('case_type', analysis)
        self.assertIn('jurisdiction', analysis)
        self.assertIn('risk_assessment', analysis)
        self.assertIn('recommendations', analysis)
        self.assertIn('statute_of_limitations', analysis)
        
        # Verify data persistence
        saved_analysis = self.analyzer.get_analysis_history(session_id)
        self.assertEqual(len(saved_analysis), 1)

class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        """Set up test environment"""
        self.analyzer = LegalSituationAnalyzer()
        
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs"""
        invalid_inputs = [
            None,
            {},
            {'description': ''},  # Empty description
            {'description': 'a' * 10000},  # Very long description
            {'date': 'invalid-date-format'}
        ]
        
        for invalid_input in invalid_inputs:
            result = self.analyzer.analyze(invalid_input)
            self.assertIn('error', result)
            
    def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        with patch('sqlite3.connect', side_effect=sqlite3.OperationalError):
            analyzer = LegalSituationAnalyzer()
            result = analyzer.create_session()
            self.assertIsNone(result)
            
    def test_model_failure_handling(self):
        """Test handling of model failures"""
        with patch.object(LegalModel, 'predict', side_effect=Exception('Model error')):
            analyzer = LegalSituationAnalyzer()
            result = analyzer.analyze({'description': 'Test case'})
            self.assertIn('error', result)

class TestPerformance(unittest.TestCase):
    """Performance and load tests"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.analyzer = LegalSituationAnalyzer()
        
    def test_analysis_speed(self):
        """Test analysis completes within reasonable time"""
        start_time = time.time()
        
        result = self.analyzer.analyze({
            'description': 'Standard legal case description',
            'date': '2024-01-01'
        })
        
        elapsed_time = time.time() - start_time
        self.assertLess(elapsed_time, 5.0)  # Should complete within 5 seconds
        
    def test_concurrent_sessions(self):
        """Test handling multiple concurrent sessions"""
        session_ids = []
        
        # Create multiple sessions
        for _ in range(10):
            session_id = self.analyzer.create_session()
            session_ids.append(session_id)
            
        # Verify all sessions are valid
        for session_id in session_ids:
            self.assertTrue(self.analyzer.is_session_valid(session_id))

if __name__ == '__main__':
    # Run tests with coverage report
    unittest.main(verbosity=2)