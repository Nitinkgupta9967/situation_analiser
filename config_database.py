"""
Configuration and Database Management for Legal Situation Analyzer
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configuration Settings
class Config:
    """Application configuration"""
    
    # Database settings
    DATABASE_NAME = "legal_cases.db"
    BACKUP_INTERVAL_HOURS = 24
    
    # Model settings
    DEFAULT_SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    DEFAULT_CLASSIFICATION_MODEL = "facebook/bart-large-mnli"
    CUSTOM_MODEL_PATH = "./models/legal_classifier"
    
    # Language settings
    SUPPORTED_LANGUAGES = ["hi", "en", "mr"]  # Hindi, English, Marathi
    DEFAULT_LANGUAGE = "en"
    
    # TTS settings
    TTS_RATE = 150
    TTS_VOLUME = 0.9
    
    # Audio settings
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_CHUNK_SIZE = 1024
    AUDIO_FORMAT = "wav"
    
    # API settings
    GOOGLE_TRANSLATE_API_KEY = None  # Set this if using premium API
    
    # Security settings
    ENCRYPTION_KEY = None  # For sensitive data encryption
    SESSION_TIMEOUT_MINUTES = 30
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "legal_analyzer.log"
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        cls.DATABASE_NAME = os.getenv("DATABASE_NAME", cls.DATABASE_NAME)
        cls.DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", cls.DEFAULT_LANGUAGE)
        cls.TTS_RATE = int(os.getenv("TTS_RATE", cls.TTS_RATE))
        cls.GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", cls.LOG_LEVEL)

class DatabaseManager:
    """Comprehensive database management for legal cases"""
    
    def __init__(self, db_name: str = None):
        self.db_name = db_name or Config.DATABASE_NAME
        self.setup_database()
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_database(self):
        """Create database tables with comprehensive schema"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Main cases table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    session_id TEXT,
                    original_text TEXT NOT NULL,
                    translated_text TEXT,
                    detected_language TEXT,
                    confidence_score REAL,
                    category TEXT,
                    subcategory TEXT,
                    urgency_level TEXT,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    summary TEXT,
                    status TEXT DEFAULT 'active',
                    is_confirmed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Legal advice table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS legal_advice (
                    advice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    advice_type TEXT,
                    recommendation TEXT,
                    applicable_law TEXT,
                    urgency_level TEXT,
                    estimated_cost TEXT,
                    timeline TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases (case_id)
                )
            ''')
            
            # Extracted entities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extracted_entities (
                    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    entity_type TEXT,
                    entity_value TEXT,
                    confidence_score REAL,
                    start_position INTEGER,
                    end_position INTEGER,
                    FOREIGN KEY (case_id) REFERENCES cases (case_id)
                )
            ''')
            
            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    interaction_count INTEGER DEFAULT 0,
                    language_preference TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Legal knowledge base table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS legal_knowledge (
                    knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    subcategory TEXT,
                    law_section TEXT,
                    description TEXT,
                    keywords TEXT,
                    applicability TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    session_id TEXT,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    feedback_text TEXT,
                    feedback_category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases (case_id)
                )
            ''')
            
            # Model performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_performance (
                    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    accuracy_score REAL,
                    precision_score REAL,
                    recall_score REAL,
                    f1_score REAL,
                    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    dataset_size INTEGER,
                    notes TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cases_category ON cases (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cases_language ON cases (detected_language)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cases_urgency ON cases (urgency_level)')
            
            conn.commit()
            
        self.logger.info("Database setup completed successfully")
    
    def insert_case(self, case_data: Dict) -> int:
        """Insert a new legal case"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO cases (
                    user_id, session_id, original_text, translated_text, 
                    detected_language, confidence_score, category, subcategory,
                    urgency_level, sentiment_score, sentiment_label, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case_data.get('user_id'),
                case_data.get('session_id'),
                case_data['original_text'],
                case_data.get('translated_text'),
                case_data.get('detected_language'),
                case_data.get('confidence_score'),
                case_data.get('category'),
                case_data.get('subcategory'),
                case_data.get('urgency_level'),
                case_data.get('sentiment_score'),
                case_data.get('sentiment_label'),
                case_data.get('summary')
            ))
            
            case_id = cursor.lastrowid
            conn.commit()
            
        self.logger.info(f"New case inserted with ID: {case_id}")
        return case_id
    
    def insert_legal_advice(self, case_id: int, advice_data: Dict):
        """Insert legal advice for a case"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            for advice in advice_data.get('recommendations', []):
                cursor.execute('''
                    INSERT INTO legal_advice (
                        case_id, advice_type, recommendation, applicable_law,
                        urgency_level, estimated_cost, timeline
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case_id,
                    advice_data.get('type', 'general'),
                    advice,
                    json.dumps(advice_data.get('applicable_laws', [])),
                    advice_data.get('urgency_level'),
                    advice_data.get('estimated_cost'),
                    advice_data.get('timeline')
                ))
            
            conn.commit()
        
        self.logger.info(f"Legal advice inserted for case ID: {case_id}")
    
    def insert_extracted_entities(self, case_id: int, entities: List[Dict]):
        """Insert extracted entities for a case"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            for entity in entities:
                cursor.execute('''
                    INSERT INTO extracted_entities (
                        case_id, entity_type, entity_value, confidence_score,
                        start_position, end_position
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    case_id,
                    entity.get('type'),
                    entity.get('value'),
                    entity.get('confidence', 0.0),
                    entity.get('start', 0),
                    entity.get('end', 0)
                ))
            
            conn.commit()
        
        self.logger.info(f"Entities inserted for case ID: {case_id}")
    
    def get_cases_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Retrieve cases by category"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM cases 
                WHERE category = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (category, limit))
            
            cases = cursor.fetchall()
            
            # Convert to dictionaries
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, case)) for case in cases]
    
    def get_case_with_advice(self, case_id: int) -> Optional[Dict]:
        """Get complete case information with advice"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Get case details
            cursor.execute('SELECT * FROM cases WHERE case_id = ?', (case_id,))
            case = cursor.fetchone()
            
            if not case:
                return None
            
            columns = [description[0] for description in cursor.description]
            case_dict = dict(zip(columns, case))
            
            # Get legal advice
            cursor.execute('''
                SELECT * FROM legal_advice WHERE case_id = ?
            ''', (case_id,))
            advice = cursor.fetchall()
            
            advice_columns = [description[0] for description in cursor.description]
            case_dict['advice'] = [dict(zip(advice_columns, adv)) for adv in advice]
            
            # Get extracted entities
            cursor.execute('''
                SELECT * FROM extracted_entities WHERE case_id = ?
            ''', (case_id,))
            entities = cursor.fetchall()
            
            entity_columns = [description[0] for description in cursor.description]
            case_dict['entities'] = [dict(zip(entity_columns, ent)) for ent in entities]
            
            return case_dict
    
    def update_case_status(self, case_id: int, status: str):
        """Update case status"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE cases 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE case_id = ?
            ''', (status, case_id))
            conn.commit()
        
        self.logger.info(f"Case {case_id} status updated to {status}")
    
    def confirm_case_summary(self, case_id: int):
        """Mark case summary as confirmed by user"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE cases 
                SET is_confirmed = TRUE, updated_at = CURRENT_TIMESTAMP 
                WHERE case_id = ?
            ''', (case_id,))
            conn.commit()
        
        self.logger.info(f"Case {case_id} summary confirmed")
    
    def insert_user_feedback(self, case_id: int, session_id: str, rating: int, feedback_text: str, feedback_category: str = 'general'):
        """Insert user feedback"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_feedback (case_id, session_id, rating, feedback_text, feedback_category)
                VALUES (?, ?, ?, ?, ?)
            ''', (case_id, session_id, rating, feedback_text, feedback_category))
            conn.commit()
        
        self.logger.info(f"Feedback inserted for case {case_id}")
    
    def get_analytics_data(self) -> Dict:
        """Get analytics data for dashboard"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            analytics = {}
            
            # Total cases
            cursor.execute('SELECT COUNT(*) FROM cases')
            analytics['total_cases'] = cursor.fetchone()[0]
            
            # Cases by category
            cursor.execute('''
                SELECT category, COUNT(*) as count 
                FROM cases 
                GROUP BY category 
                ORDER BY count DESC
            ''')
            analytics['cases_by_category'] = dict(cursor.fetchall())
            
            # Cases by language
            cursor.execute('''
                SELECT detected_language, COUNT(*) as count 
                FROM cases 
                GROUP BY detected_language 
                ORDER BY count DESC
            ''')
            analytics['cases_by_language'] = dict(cursor.fetchall())
            
            # Cases by urgency
            cursor.execute('''
                SELECT urgency_level, COUNT(*) as count 
                FROM cases 
                GROUP BY urgency_level 
                ORDER BY count DESC
            ''')
            analytics['cases_by_urgency'] = dict(cursor.fetchall())
            
            # Average rating
            cursor.execute('SELECT AVG(rating) FROM user_feedback')
            avg_rating = cursor.fetchone()[0]
            analytics['average_rating'] = round(avg_rating, 2) if avg_rating else 0
            
            # Cases per day (last 30 days)
            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM cases 
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            analytics['cases_per_day'] = dict(cursor.fetchall())
            
            return analytics
    
    def cleanup_old_sessions(self, days: int = 7):
        """Clean up old inactive sessions"""
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET status = 'expired'
                WHERE start_time < datetime('now', '-{} days')
                AND status = 'active'
            '''.format(days))
            conn.commit()
            
            deleted_count = cursor.rowcount
            
        self.logger.info(f"Cleaned up {deleted_count} old sessions")
        return deleted_count
    
    def backup_database(self, backup_path: str = None):
        """Create database backup"""
        
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{self.db_name}_{timestamp}"
        
        with sqlite3.connect(self.db_name) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        self.logger.info(f"Database backed up to {backup_path}")
        return backup_path

class LegalKnowledgeBase:
    """Manage legal knowledge base"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.populate_initial_knowledge()
    
    def populate_initial_knowledge(self):
        """Populate initial legal knowledge"""
        
        legal_knowledge = [
            {
                'category': 'family',
                'subcategory': 'divorce',
                'law_section': 'Hindu Marriage Act, 1955 - Section 13',
                'description': 'Grounds for divorce including cruelty, desertion, adultery, conversion, mental disorder, and communicable disease',
                'keywords': 'divorce, cruelty, desertion, adultery, mental disorder',
                'applicability': 'Hindus, Buddhists, Sikhs, Jains'
            },
            {
                'category': 'criminal',
                'subcategory': 'theft',
                'law_section': 'Indian Penal Code, 1860 - Section 378',
                'description': 'Whoever intends to take dishonestly any movable property out of the possession of any person without that person\'s consent',
                'keywords': 'theft, stealing, dishonestly, movable property',
                'applicability': 'All citizens of India'
            },
            {
                'category': 'property',
                'subcategory': 'registration',
                'law_section': 'Registration Act, 1908 - Section 17',
                'description': 'Documents relating to immovable property must be registered',
                'keywords': 'property registration, immovable property, documents',
                'applicability': 'All property transactions in India'
            },
            {
                'category': 'employment',
                'subcategory': 'termination',
                'law_section': 'Industrial Disputes Act, 1947 - Section 25F',
                'description': 'Conditions for valid retrenchment including notice period and compensation',
                'keywords': 'termination, retrenchment, notice period, compensation',
                'applicability': 'Industrial establishments with 50 or more workers'
            },
            {
                'category': 'consumer',
                'subcategory': 'defective_goods',
                'law_section': 'Consumer Protection Act, 2019 - Section 2(5)',
                'description': 'Definition of defective goods and consumer rights',
                'keywords': 'defective goods, consumer rights, refund, replacement',
                'applicability': 'All consumers purchasing goods or services'
            }
        ]
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            
            for knowledge in legal_knowledge:
                cursor.execute('''
                    INSERT OR IGNORE INTO legal_knowledge 
                    (category, subcategory, law_section, description, keywords, applicability)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    knowledge['category'],
                    knowledge['subcategory'],
                    knowledge['law_section'],
                    knowledge['description'],
                    knowledge['keywords'],
                    knowledge['applicability']
                ))
            
            conn.commit()
    
    def search_knowledge(self, query: str, category: str = None) -> List[Dict]:
        """Search legal knowledge base"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT * FROM legal_knowledge 
                    WHERE (keywords LIKE ? OR description LIKE ?) 
                    AND category = ?
                    ORDER BY updated_at DESC
                ''', (f'%{query}%', f'%{query}%', category))
            else:
                cursor.execute('''
                    SELECT * FROM legal_knowledge 
                    WHERE keywords LIKE ? OR description LIKE ?
                    ORDER BY updated_at DESC
                ''', (f'%{query}%', f'%{query}%'))
            
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            return [dict(zip(columns, result)) for result in results]
    
    def get_laws_by_category(self, category: str) -> List[Dict]:
        """Get all laws for a specific category"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM legal_knowledge 
                WHERE category = ?
                ORDER BY subcategory, law_section
            ''', (category,))
            
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            return [dict(zip(columns, result)) for result in results]
    
    def add_knowledge(self, knowledge_data: Dict):
        """Add new legal knowledge"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO legal_knowledge 
                (category, subcategory, law_section, description, keywords, applicability)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                knowledge_data['category'],
                knowledge_data['subcategory'],
                knowledge_data['law_section'],
                knowledge_data['description'],
                knowledge_data['keywords'],
                knowledge_data['applicability']
            ))
            conn.commit()

class SessionManager:
    """Manage user sessions"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_session(self, user_id: str = None, language_preference: str = 'en') -> str:
        """Create new user session"""
        
        import uuid
        session_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions (session_id, user_id, language_preference)
                VALUES (?, ?, ?)
            ''', (session_id, user_id, language_preference))
            conn.commit()
        
        return session_id
    
    def update_session_activity(self, session_id: str):
        """Update session activity"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET interaction_count = interaction_count + 1
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
    
    def end_session(self, session_id: str):
        """End user session"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions 
                SET end_time = CURRENT_TIMESTAMP, status = 'ended'
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        
        with sqlite3.connect(self.db_manager.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_sessions WHERE session_id = ?
            ''', (session_id,))
            
            session = cursor.fetchone()
            if session:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, session))
            
            return None

# Example usage and testing
if __name__ == "__main__":
    # Initialize configuration
    Config.load_from_env()
    
    # Initialize database
    db_manager = DatabaseManager()
    
    # Initialize knowledge base
    knowledge_base = LegalKnowledgeBase(db_manager)
    
    # Initialize session manager
    session_manager = SessionManager(db_manager)
    
    # Example: Create a session
    session_id = session_manager.create_session(language_preference='hi')
    print(f"Created session: {session_id}")
    
    # Example: Insert a case
    case_data = {
        'session_id': session_id,
        'original_text': 'मेरे पति ने मुझे तलाक दे दिया है',
        'translated_text': 'My husband has divorced me',
        'detected_language': 'hi',
        'category': 'family',
        'urgency_level': 'medium',
        'summary': 'Divorce case requiring legal assistance'
    }
    
    case_id = db_manager.insert_case(case_data)
    print(f"Inserted case with ID: {case_id}")
    
    # Example: Get analytics
    analytics = db_manager.get_analytics_data()
    print("Analytics data:", analytics)
    
    # Example: Search knowledge base
    results = knowledge_base.search_knowledge('divorce', 'family')
    print(f"Found {len(results)} relevant laws")
    
    # Example: Create backup
    backup_path = db_manager.backup_database()
    print(f"Database backed up to: {backup_path}")
    
    print("Database setup and testing completed successfully!")