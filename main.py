"""
Legal Situation Analyzer - Main Application
A comprehensive legal assistant that analyzes user situations in Hindi, English, and Marathi
"""

import streamlit as st
import speech_recognition as sr
import pyttsx3
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import json
import re
from datetime import datetime
import sqlite3
from googletrans import Translator
import warnings
warnings.filterwarnings("ignore")

class LegalSituationAnalyzer:
    def __init__(self):
        self.translator = Translator()
        self.setup_database()
        self.setup_models()
        self.setup_tts()
        self.legal_categories = {
            'family': ['divorce', 'custody', 'marriage', 'property', 'inheritance'],
            'criminal': ['theft', 'assault', 'fraud', 'harassment', 'violence'],
            'civil': ['contract', 'debt', 'defamation', 'negligence', 'breach'],
            'property': ['rent', 'eviction', 'ownership', 'dispute', 'registration'],
            'employment': ['salary', 'termination', 'harassment', 'rights', 'compensation'],
            'consumer': ['refund', 'warranty', 'service', 'product', 'complaint']
        }
        
    def setup_database(self):
        """Initialize SQLite database for storing conversations"""
        self.conn = sqlite3.connect('legal_cases.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                original_text TEXT,
                translated_text TEXT,
                language TEXT,
                category TEXT,
                summary TEXT,
                recommendations TEXT,
                applicable_laws TEXT
            )
        ''')
        self.conn.commit()
    
    def setup_models(self):
        """Initialize ML models for text analysis"""
        try:
            # Load sentiment analysis model
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            
            # Load text classification model for legal categories
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
            
        except Exception as e:
            st.error(f"Error loading models: {e}")
            
    def setup_tts(self):
        """Initialize text-to-speech engine"""
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        
    def detect_language(self, text):
        """Detect the language of input text"""
        try:
            detected = self.translator.detect(text)
            return detected.lang
        except:
            return 'en'
    
    def translate_text(self, text, target_lang='en'):
        """Translate text to target language"""
        try:
            if self.detect_language(text) == target_lang:
                return text
            translated = self.translator.translate(text, dest=target_lang)
            return translated.text
        except:
            return text
    
    def extract_key_info(self, text):
        """Extract key information from the legal situation"""
        # Common legal keywords in multiple languages
        keywords = {
            'english': ['contract', 'agreement', 'dispute', 'court', 'lawyer', 'case', 'legal', 'law'],
            'hindi': ['कानूनी', 'न्यायालय', 'वकील', 'मामला', 'विवाद', 'समझौता'],
            'marathi': ['कायदेशीर', 'न्यायालय', 'वकील', 'प्रकरण', 'वाद', 'करार']
        }
        
        extracted_info = {
            'parties_involved': [],
            'legal_keywords': [],
            'dates': [],
            'amounts': [],
            'locations': []
        }
        
        # Extract dates
        date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'
        extracted_info['dates'] = re.findall(date_pattern, text)
        
        # Extract amounts
        amount_pattern = r'₹\s*\d+(?:,\d+)*|\$\s*\d+(?:,\d+)*|\d+\s*(?:rupees|dollars|lakh|crore)'
        extracted_info['amounts'] = re.findall(amount_pattern, text, re.IGNORECASE)
        
        # Extract legal keywords
        text_lower = text.lower()
        for lang, words in keywords.items():
            for word in words:
                if word.lower() in text_lower:
                    extracted_info['legal_keywords'].append(word)
        
        return extracted_info
    
    def categorize_legal_issue(self, text):
        """Categorize the legal issue using ML"""
        try:
            categories = list(self.legal_categories.keys())
            result = self.classifier(text, categories)
            
            primary_category = result['labels'][0]
            confidence = result['scores'][0]
            
            return {
                'category': primary_category,
                'confidence': confidence,
                'subcategories': self.legal_categories.get(primary_category, [])
            }
        except:
            return {'category': 'general', 'confidence': 0.5, 'subcategories': []}
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of the legal situation"""
        try:
            result = self.sentiment_analyzer(text)
            return result[0]
        except:
            return {'label': 'NEUTRAL', 'score': 0.5}
    
    def generate_legal_advice(self, category, text, extracted_info):
        """Generate legal advice based on category and extracted information"""
        advice_templates = {
            'family': {
                'steps': [
                    "Document all relevant communications and agreements",
                    "Consult with a family law specialist",
                    "Consider mediation before litigation",
                    "Gather all financial documents",
                    "Understand your rights under family laws"
                ],
                'laws': [
                    "Hindu Marriage Act, 1955",
                    "Indian Succession Act, 1925",
                    "Protection of Women from Domestic Violence Act, 2005",
                    "Guardians and Wards Act, 1890"
                ]
            },
            'criminal': {
                'steps': [
                    "File an FIR at the nearest police station immediately",
                    "Preserve all evidence related to the incident",
                    "Consult with a criminal lawyer",
                    "Cooperate with police investigation",
                    "Keep records of all proceedings"
                ],
                'laws': [
                    "Indian Penal Code, 1860",
                    "Code of Criminal Procedure, 1973",
                    "Indian Evidence Act, 1872",
                    "Protection of Women from Sexual Harassment Act, 2013"
                ]
            },
            'civil': {
                'steps': [
                    "Send a legal notice to the other party",
                    "Gather all relevant documents and evidence",
                    "Attempt alternative dispute resolution",
                    "File a civil suit if necessary",
                    "Maintain detailed records"
                ],
                'laws': [
                    "Code of Civil Procedure, 1908",
                    "Indian Contract Act, 1872",
                    "Specific Relief Act, 1963",
                    "Limitation Act, 1963"
                ]
            },
            'property': {
                'steps': [
                    "Verify property documents and titles",
                    "Check for any encumbrances or disputes",
                    "Consult with a property lawyer",
                    "Register the property properly",
                    "Maintain all transaction records"
                ],
                'laws': [
                    "Transfer of Property Act, 1882",
                    "Registration Act, 1908",
                    "Indian Stamp Act, 1899",
                    "Real Estate Regulation Act, 2016"
                ]
            },
            'employment': {
                'steps': [
                    "Review your employment contract",
                    "Document workplace incidents",
                    "File complaints with appropriate authorities",
                    "Seek legal consultation",
                    "Understand your labor rights"
                ],
                'laws': [
                    "Industrial Disputes Act, 1947",
                    "Minimum Wages Act, 1948",
                    "Employees' Provident Fund Act, 1952",
                    "Sexual Harassment of Women at Workplace Act, 2013"
                ]
            },
            'consumer': {
                'steps': [
                    "File a complaint with consumer forum",
                    "Gather purchase receipts and warranties",
                    "Document all communications with seller",
                    "Seek compensation for damages",
                    "Know your consumer rights"
                ],
                'laws': [
                    "Consumer Protection Act, 2019",
                    "Indian Contract Act, 1872",
                    "Sale of Goods Act, 1930",
                    "Competition Act, 2002"
                ]
            }
        }
        
        template = advice_templates.get(category, advice_templates['civil'])
        
        # Customize advice based on extracted information
        customized_steps = template['steps'].copy()
        
        if extracted_info['amounts']:
            customized_steps.append(f"The monetary value involved ({', '.join(extracted_info['amounts'])}) may affect the jurisdiction and court fees")
        
        if extracted_info['dates']:
            customized_steps.append("Pay attention to limitation periods for legal action")
        
        return {
            'recommended_steps': customized_steps,
            'applicable_laws': template['laws'],
            'urgency_level': self.assess_urgency(text, category)
        }
    
    def assess_urgency(self, text, category):
        """Assess the urgency level of the legal situation"""
        urgent_keywords = ['emergency', 'urgent', 'immediate', 'threat', 'violence', 'harassment', 'eviction']
        text_lower = text.lower()
        
        urgency_score = 0
        for keyword in urgent_keywords:
            if keyword in text_lower:
                urgency_score += 1
        
        if category == 'criminal':
            urgency_score += 2
        
        if urgency_score >= 3:
            return 'HIGH'
        elif urgency_score >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def create_situation_summary(self, original_text, translated_text, category_info, extracted_info, sentiment):
        """Create a comprehensive situation summary"""
        summary = f"""
        **LEGAL SITUATION SUMMARY**
        
        **Primary Category:** {category_info['category'].title()}
        **Confidence Level:** {category_info['confidence']:.2%}
        
        **Key Information Extracted:**
        - Legal Keywords Found: {', '.join(extracted_info['legal_keywords']) if extracted_info['legal_keywords'] else 'None'}
        - Dates Mentioned: {', '.join(extracted_info['dates']) if extracted_info['dates'] else 'None'}
        - Monetary Values: {', '.join(extracted_info['amounts']) if extracted_info['amounts'] else 'None'}
        
        **Situation Sentiment:** {sentiment['label']} (Confidence: {sentiment['score']:.2%})
        
        **Situation Description:**
        {translated_text}
        """
        
        return summary.strip()
    
    def save_case(self, original_text, translated_text, language, category, summary, recommendations, laws):
        """Save case to database"""
        timestamp = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT INTO cases (timestamp, original_text, translated_text, language, category, summary, recommendations, applicable_laws)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, original_text, translated_text, language, category, summary, json.dumps(recommendations), json.dumps(laws)))
        self.conn.commit()
    
    def text_to_speech(self, text, language='en'):
        """Convert text to speech"""
        try:
            # Translate to English for TTS if needed
            if language != 'en':
                text = self.translate_text(text, 'en')
            
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            st.error(f"TTS Error: {e}")

def main():
    st.set_page_config(
        page_title="Legal Situation Analyzer",
        page_icon="⚖️",
        layout="wide"
    )
    
    st.title("⚖️ Legal Situation Analyzer")
    st.subtitle("Multilingual Legal Assistant (Hindi | English | Marathi)")
    
    # Initialize the analyzer
    if 'analyzer' not in st.session_state:
        with st.spinner("Loading AI models..."):
            st.session_state.analyzer = LegalSituationAnalyzer()
    
    analyzer = st.session_state.analyzer
    
    # Sidebar for options
    st.sidebar.title("Options")
    input_method = st.sidebar.radio("Choose Input Method:", ["Text", "Voice"])
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Describe Your Legal Situation")
        
        if input_method == "Text":
            user_input = st.text_area(
                "Enter your legal situation in Hindi, English, or Marathi:",
                height=200,
                placeholder="आप अपनी कानूनी समस्या यहाँ लिख सकते हैं... | You can write your legal problem here... | तुम्ही तुमची कायदेशीर समस्या येथे लिहू शकता..."
            )
        else:
            st.info("Voice input feature requires additional setup. Please use text input for now.")
            user_input = st.text_area("Fallback - Enter your situation:", height=200)
        
        if st.button("🔍 Analyze Situation", type="primary"):
            if user_input:
                with st.spinner("Analyzing your legal situation..."):
                    # Detect language and translate
                    detected_lang = analyzer.detect_language(user_input)
                    translated_text = analyzer.translate_text(user_input, 'en')
                    
                    # Extract information
                    extracted_info = analyzer.extract_key_info(translated_text)
                    category_info = analyzer.categorize_legal_issue(translated_text)
                    sentiment = analyzer.analyze_sentiment(translated_text)
                    
                    # Generate summary
                    summary = analyzer.create_situation_summary(
                        user_input, translated_text, category_info, extracted_info, sentiment
                    )
                    
                    # Generate advice
                    advice = analyzer.generate_legal_advice(
                        category_info['category'], translated_text, extracted_info
                    )
                    
                    # Store in session state
                    st.session_state.analysis_results = {
                        'original_text': user_input,
                        'translated_text': translated_text,
                        'detected_lang': detected_lang,
                        'summary': summary,
                        'advice': advice,
                        'category_info': category_info,
                        'extracted_info': extracted_info,
                        'sentiment': sentiment
                    }
    
    with col2:
        st.header("Analysis Tools")
        
        if st.button("🎤 Voice Input"):
            st.info("Voice recognition feature coming soon!")
        
        if st.button("📊 View Case History"):
            # Display recent cases from database
            recent_cases = analyzer.cursor.execute(
                "SELECT * FROM cases ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            
            if recent_cases:
                st.subheader("Recent Cases")
                for case in recent_cases:
                    with st.expander(f"Case {case[0]} - {case[5]}"):
                        st.write(f"**Date:** {case[1]}")
                        st.write(f"**Category:** {case[5]}")
                        st.write(f"**Summary:** {case[6]}")
    
    # Display results
    if 'analysis_results' in st.session_state:
        results = st.session_state.analysis_results
        
        st.divider()
        st.header("📋 Analysis Results")
        
        # Summary section
        with st.expander("📝 Situation Summary", expanded=True):
            st.markdown(results['summary'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Summary"):
                    st.success("Summary confirmed! Proceeding with recommendations.")
            with col2:
                if st.button("✏️ Request Modification"):
                    st.info("Please provide additional details or corrections above.")
        
        # Recommendations section
        st.subheader("💡 Recommended Actions")
        urgency = results['advice']['urgency_level']
        
        if urgency == 'HIGH':
            st.error("⚠️ HIGH URGENCY - Immediate action required!")
        elif urgency == 'MEDIUM':
            st.warning("⚡ MEDIUM URGENCY - Action needed soon")
        else:
            st.info("📅 NORMAL URGENCY - Plan your next steps")
        
        st.write("**Steps you should take:**")
        for i, step in enumerate(results['advice']['recommended_steps'], 1):
            st.write(f"{i}. {step}")
        
        # Applicable laws
        st.subheader("📚 Applicable Laws")
        for law in results['advice']['applicable_laws']:
            st.write(f"• {law}")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Case"):
                analyzer.save_case(
                    results['original_text'],
                    results['translated_text'],
                    results['detected_lang'],
                    results['category_info']['category'],
                    results['summary'],
                    results['advice']['recommended_steps'],
                    results['advice']['applicable_laws']
                )
                st.success("Case saved successfully!")
        
        with col2:
            if st.button("🔊 Read Aloud"):
                with st.spinner("Converting to speech..."):
                    analyzer.text_to_speech(results['summary'])
                st.success("Audio playback completed!")
        
        with col3:
            if st.button("📤 Export Report"):
                report = f"""
                LEGAL SITUATION ANALYSIS REPORT
                Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                {results['summary']}
                
                RECOMMENDED ACTIONS:
                {chr(10).join(f'{i}. {step}' for i, step in enumerate(results['advice']['recommended_steps'], 1))}
                
                APPLICABLE LAWS:
                {chr(10).join(f'• {law}' for law in results['advice']['applicable_laws'])}
                """
                
                st.download_button(
                    label="Download Report",
                    data=report,
                    file_name=f"legal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()