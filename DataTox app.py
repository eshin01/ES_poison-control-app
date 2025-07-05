"""
Poison Control AI Assistant - Python/Streamlit Version
A medical documentation and research platform for poison control centers
"""

import streamlit as st
import pandas as pd
import json
import re
import datetime
from typing import Dict, List, Optional, Any
import uuid
import io
from dataclasses import dataclass, asdict
from pathlib import Path
import speech_recognition as sr
import threading
import time

# Page configuration
st.set_page_config(
    page_title="🏥 Poison Control AI Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
SEVERITY_LEVELS = {
    'MINIMAL': {'level': 1, 'color': 'green', 'description': 'No treatment expected', 'icon': '🟢'},
    'MINOR': {'level': 2, 'color': 'yellow', 'description': 'Minimal treatment expected', 'icon': '🟡'},
    'MODERATE': {'level': 3, 'color': 'orange', 'description': 'Treatment required', 'icon': '🟠'},
    'MAJOR': {'level': 4, 'color': 'red', 'description': 'Life-threatening', 'icon': '🔴'},
    'FATAL': {'level': 5, 'color': 'black', 'description': 'Death resulted', 'icon': '⚫'}
}

COMMON_SUBSTANCES = [
    'Acetaminophen/Tylenol', 'Ibuprofen', 'Aspirin', 'Household cleaners',
    'Bleach', 'Alcohol', 'Cannabis', 'Prescription medications',
    'Vitamins/supplements', 'Plants', 'Cosmetics', 'Arts/crafts supplies'
]

VALIDATION_RULES = {
    'case_id': {'required': True, 'pattern': r'^CASE-\d+-[A-Z0-9]{5}$'},
    'first_name': {'required': True, 'min_length': 1, 'max_length': 50},
    'last_name': {'required': True, 'min_length': 1, 'max_length': 50},
    'dob': {'required': True, 'pattern': r'^\d{4}-\d{2}-\d{2}$'},
    'age': {'required': True, 'min': 0, 'max': 150},
    'specialist_name': {'required': True, 'min_length': 2, 'max_length': 100},
    'substances': {'required': True, 'min_length': 1, 'max_length': 500},
}

@dataclass
class PoisonCase:
    """Data class for poison control cases"""
    case_id: str
    call_date: str
    call_time: str
    specialist_name: str
    first_name: str
    last_name: str
    dob: str
    age: int
    substances: str
    hpi: str
    physical_exam: str
    recommendations: str
    severity: str = 'MINIMAL'
    follow_up_required: bool = False
    emergency_department_recommended: bool = False
    substance_keywords: List[str] = None
    last_updated: str = None
    version: int = 1
    updates: List[Dict] = None

    def __post_init__(self):
        if self.substance_keywords is None:
            self.substance_keywords = self._generate_keywords()
        if self.last_updated is None:
            self.last_updated = datetime.datetime.now().isoformat()
        if self.updates is None:
            self.updates = []

    def _generate_keywords(self) -> List[str]:
        """Generate searchable keywords from substances"""
        if not self.substances:
            return []
        return [kw.strip().lower() for kw in re.split(r'[\s,()]+', self.substances) if kw.strip()]

class DataStore:
    """Manages data storage and retrieval"""
    
    def __init__(self):
        self.data_file = Path("poison_cases.json")
        self.cases = self._load_cases()
    
    def _load_cases(self) -> Dict[str, PoisonCase]:
        """Load cases from JSON file"""
        if not self.data_file.exists():
            return {}
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                cases = {}
                for case_id, case_data in data.items():
                    # Convert dict back to PoisonCase object
                    case = PoisonCase(**case_data)
                    cases[case_id] = case
                return cases
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            st.error(f"Error loading cases: {e}")
            return {}
    
    def _save_cases(self):
        """Save cases to JSON file"""
        try:
            data = {}
            for case_id, case in self.cases.items():
                data[case_id] = asdict(case)
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            st.error(f"Error saving cases: {e}")
    
    def save_case(self, case: PoisonCase) -> bool:
        """Save a case to storage"""
        try:
            case.last_updated = datetime.datetime.now().isoformat()
            case.version += 1
            self.cases[case.case_id] = case
            self._save_cases()
            return True
        except Exception as e:
            st.error(f"Error saving case: {e}")
            return False
    
    def get_cases(self) -> List[PoisonCase]:
        """Get all cases sorted by last updated"""
        cases_list = list(self.cases.values())
        return sorted(cases_list, key=lambda x: x.last_updated, reverse=True)
    
    def search_cases(self, search_term: str = "", severity_filter: str = "") -> List[PoisonCase]:
        """Search and filter cases"""
        cases = self.get_cases()
        
        if search_term:
            search_lower = search_term.lower()
            cases = [c for c in cases if 
                search_lower in c.case_id.lower() or
                search_lower in c.first_name.lower() or
                search_lower in c.last_name.lower() or
                search_lower in c.substances.lower() or
                any(search_lower in kw for kw in c.substance_keywords)
            ]
        
        if severity_filter and severity_filter != "All":
            cases = [c for c in cases if c.severity == severity_filter]
        
        return cases

class TranscriptProcessor:
    """Processes transcripts and extracts medical information"""
    
    @staticmethod
    def extract_data_from_transcript(transcript: str) -> Dict[str, Any]:
        """Extract structured data from transcript using pattern matching"""
        if not transcript:
            return {}
        
        text = transcript.strip()
        lower_text = text.lower()
        extracted = {}

        # Extract names
        name_patterns = [
            r'(?:patient|child|caller)\s+(?:is\s+)?([A-Z][a-z]+)\s+([A-Z][a-z]+)',
            r'([A-Z][a-z]+)\s+([A-Z][a-z]+)(?:,|\s+(?:is|age|born))',
            r'(?:my|his|her)\s+(?:son|daughter|child)\s+([A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2 and match.group(2):
                    extracted['first_name'] = match.group(1)
                    extracted['last_name'] = match.group(2)
                elif match.group(1):
                    extracted['first_name'] = match.group(1)
                break

        # Extract age
        age_patterns = [
            r'(\d+)[-\s]?year[-\s]?old',
            r'age\s+(\d+)',
            r'(\d+)\s*y\.?o\.?',
            r'(\d+)\s+years?\s+old'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                extracted['age'] = age
                # Estimate DOB
                current_year = datetime.datetime.now().year
                birth_year = current_year - age
                extracted['dob'] = f"{birth_year}-06-15"
                break

        # Extract specialist name
        doctor_patterns = [
            r'(?:this is|i\'m|i am)\s+(dr\.?\s+[A-Z][a-z]+)',
            r'(dr\.?\s+[A-Z][a-z]+)',
            r'specialist\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        for pattern in doctor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted['specialist_name'] = match.group(1)
                break

        # Extract substances
        substance_keywords = {
            'tylenol': 'Acetaminophen/Tylenol',
            'acetaminophen': 'Acetaminophen/Tylenol',
            'ibuprofen': 'Ibuprofen',
            'advil': 'Ibuprofen',
            'aspirin': 'Aspirin',
            'bleach': 'Bleach',
            'cleaner': 'Household cleaners',
            'alcohol': 'Alcohol',
            'vitamin': 'Vitamins/supplements',
            'medication': 'Prescription medications',
            'medicine': 'Prescription medications'
        }

        for keyword, substance in substance_keywords.items():
            if keyword in lower_text:
                extracted['substances'] = substance
                break

        # Extract timing information
        time_patterns = [
            r'(\d+)\s+minutes?\s+ago',
            r'about\s+(\d+)\s+(?:minutes?|hours?)\s+ago',
            r'(\d+)\s+hours?\s+ago'
        ]
        
        time_info = ''
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                unit = 'hours' if 'hour' in match.group(0).lower() else 'minutes'
                time_info = f" approximately {match.group(1)} {unit} ago"
                break

        # Build HPI
        if extracted.get('age') and extracted.get('substances'):
            hpi = f"{extracted['age']}-year-old patient with reported ingestion of {extracted['substances']}{time_info}. "
            
            # Add symptoms
            if any(word in lower_text for word in ['drowsy', 'sleepy', 'lethargic']):
                hpi += "Patient appears drowsy/lethargic. "
            if 'vomit' in lower_text:
                hpi += "Reports vomiting. "
            if any(word in lower_text for word in ['conscious', 'alert']):
                hpi += "Patient remains conscious and alert. "
            
            extracted['hpi'] = hpi

        # Determine severity and recommendations
        if any(word in lower_text for word in ['emergency', 'hospital', 'transport']):
            extracted['severity'] = 'MODERATE'
            extracted['emergency_department_recommended'] = True
            extracted['recommendations'] = 'Recommend immediate transport to emergency department for evaluation and possible treatment.'
        elif any(word in lower_text for word in ['drowsy', 'lethargic', 'sleepy']):
            extracted['severity'] = 'MINOR'
            extracted['recommendations'] = 'Monitor patient closely. Consider medical evaluation if symptoms worsen.'
            extracted['follow_up_required'] = True
        else:
            extracted['severity'] = 'MINIMAL'
            extracted['recommendations'] = 'Monitor for symptoms. Provide supportive care as needed.'

        # Set defaults for missing fields
        defaults = {
            'first_name': 'Patient',
            'last_name': 'Unknown',
            'specialist_name': 'Poison Control Specialist',
            'substances': 'Unknown substance',
            'hpi': 'Patient with reported substance exposure. Further details needed.',
            'recommendations': 'Assess patient and provide appropriate care based on clinical presentation.',
            'severity': 'MINIMAL'
        }
        
        for key, default_value in defaults.items():
            if key not in extracted:
                extracted[key] = default_value

        return extracted

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_case_data(case_data: Dict[str, Any]) -> List[str]:
    """Validate case data and return list of errors"""
    errors = []
    
    for field, rules in VALIDATION_RULES.items():
        value = case_data.get(field)
        
        if rules.get('required') and (not value or str(value).strip() == ''):
            errors.append(f"{field.replace('_', ' ').title()} is required")
            continue
        
        if value is not None:
            str_value = str(value)
            
            if 'pattern' in rules and not re.match(rules['pattern'], str_value):
                errors.append(f"{field.replace('_', ' ').title()} format is invalid")
            
            if 'min_length' in rules and len(str_value) < rules['min_length']:
                errors.append(f"{field.replace('_', ' ').title()} must be at least {rules['min_length']} characters")
            
            if 'max_length' in rules and len(str_value) > rules['max_length']:
                errors.append(f"{field.replace('_', ' ').title()} must be no more than {rules['max_length']} characters")
            
            if 'min' in rules:
                try:
                    if float(value) < rules['min']:
                        errors.append(f"{field.replace('_', ' ').title()} must be at least {rules['min']}")
                except (ValueError, TypeError):
                    pass
            
            if 'max' in rules:
                try:
                    if float(value) < rules['max']:
                        errors.append(f"{field.replace('_', ' ').title()} must be no more than {rules['max']}")
                except (ValueError, TypeError):
                    pass
    
    return errors

def generate_case_id() -> str:
    """Generate a unique case ID"""
    timestamp = int(time.time())
    random_suffix = str(uuid.uuid4())[:5].upper()
    return f"CASE-{timestamp}-{random_suffix}"

def render_severity_badge(severity: str) -> str:
    """Render severity badge as colored text"""
    if severity in SEVERITY_LEVELS:
        info = SEVERITY_LEVELS[severity]
        return f"{info['icon']} Level {info['level']}: {info['description']}"
    return f"🔘 {severity}"

def speech_to_text() -> Optional[str]:
    """Convert speech to text using speech_recognition library"""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎤 Listening... Speak now!")
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=1)
            # Listen for audio
            audio = r.listen(source, timeout=10, phrase_time_limit=30)
            
        st.info("🔄 Processing speech...")
        # Use Google's speech recognition
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        st.error("Could not understand the audio. Please try again.")
        return None
    except sr.RequestError as e:
        st.error(f"Speech recognition service error: {e}")
        return None
    except sr.WaitTimeoutError:
        st.error("No speech detected. Please try again.")
        return None
    except Exception as e:
        st.error(f"Speech recognition error: {e}")
        return None

# Initialize session state
if 'data_store' not in st.session_state:
    st.session_state.data_store = DataStore()

if 'current_case' not in st.session_state:
    now = datetime.datetime.now()
    st.session_state.current_case = {
        'case_id': generate_case_id(),
        'call_date': now.strftime('%Y-%m-%d'),
        'call_time': now.strftime('%H:%M'),
        'specialist_name': '',
        'first_name': '',
        'last_name': '',
        'dob': '',
        'age': 0,
        'substances': '',
        'hpi': '',
        'physical_exam': '',
        'recommendations': '',
        'severity': 'MINIMAL',
        'follow_up_required': False,
        'emergency_department_recommended': False
    }

if 'transcript' not in st.session_state:
    st.session_state.transcript = ''

def main():
    """Main application function"""
    
    # Header
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1>🏥 Poison Control AI Assistant</h1>
        <p style='color: #666; font-size: 16px;'>Medical Documentation & Research Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation tabs
    tab1, tab2 = st.tabs(["📝 Data Entry", "📊 Case Management"])
    
    with tab1:
        render_data_entry()
    
    with tab2:
        render_case_management()

def render_data_entry():
    """Render the data entry interface"""
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎤 Speech Input & Transcript Processing")
        
        # Speech input section
        with st.container():
            st.markdown("**Call Transcript**")
            
            # Speech recognition button
            col_speech, col_process = st.columns([1, 1])
            
            with col_speech:
                if st.button("🎤 Start Recording", help="Click to start speech recognition"):
                    with st.spinner("Listening..."):
                        speech_text = speech_to_text()
                        if speech_text:
                            st.session_state.transcript += f" {speech_text}"
                            st.rerun()
            
            with col_process:
                if st.button("🤖 Process with AI", help="Extract data from transcript"):
                    if st.session_state.transcript.strip():
                        with st.spinner("Processing transcript..."):
                            time.sleep(1)  # Simulate processing time
                            extracted_data = TranscriptProcessor.extract_data_from_transcript(
                                st.session_state.transcript
                            )
                            
                            # Update current case with extracted data
                            for key, value in extracted_data.items():
                                if key in st.session_state.current_case:
                                    st.session_state.current_case[key] = value
                            
                            st.success("✨ AI processing complete! Data extracted successfully.")
                            st.rerun()
                    else:
                        st.error("Please enter a transcript first.")
            
            # Transcript text area
            transcript = st.text_area(
                "Enter or edit transcript:",
                value=st.session_state.transcript,
                height=200,
                placeholder="Type the call transcript here or use speech recognition above..."
            )
            
            if transcript != st.session_state.transcript:
                st.session_state.transcript = transcript
            
            # Clear transcript button
            if st.button("🗑️ Clear Transcript"):
                st.session_state.transcript = ""
                st.rerun()
    
    with col2:
        st.subheader("📋 Case Data Form")
        
        # Case Information Section
        with st.expander("📞 Case Information", expanded=True):
            case_id = st.text_input("Case ID", value=st.session_state.current_case['case_id'], disabled=True)
            
            specialist_name = st.text_input(
                "Specialist Name *", 
                value=st.session_state.current_case['specialist_name'],
                placeholder="Enter specialist name"
            )
            
            col_date, col_time = st.columns(2)
            with col_date:
                call_date = st.date_input(
                    "Call Date *", 
                    value=datetime.datetime.strptime(st.session_state.current_case['call_date'], '%Y-%m-%d').date()
                )
            
            with col_time:
                call_time = st.time_input(
                    "Call Time", 
                    value=datetime.datetime.strptime(st.session_state.current_case['call_time'], '%H:%M').time()
                )
        
        # Patient Information Section
        with st.expander("👤 Patient Information", expanded=True):
            col_fname, col_lname = st.columns(2)
            
            with col_fname:
                first_name = st.text_input(
                    "First Name *", 
                    value=st.session_state.current_case['first_name'],
                    placeholder="Patient's first name"
                )
            
            with col_lname:
                last_name = st.text_input(
                    "Last Name *", 
                    value=st.session_state.current_case['last_name'],
                    placeholder="Patient's last name"
                )
            
            col_dob, col_age = st.columns(2)
            
            with col_dob:
                dob = st.date_input(
                    "Date of Birth *",
                    value=datetime.datetime.strptime(st.session_state.current_case['dob'], '%Y-%m-%d').date() 
                          if st.session_state.current_case['dob'] else None
                )
            
            with col_age:
                age = st.number_input(
                    "Age *", 
                    min_value=0, 
                    max_value=150, 
                    value=st.session_state.current_case['age'],
                    step=1
                )
        
        # Clinical Information Section
        with st.expander("🏥 Clinical Information", expanded=True):
            substances = st.selectbox(
                "Substance(s) Involved *",
                options=[''] + COMMON_SUBSTANCES,
                index=COMMON_SUBSTANCES.index(st.session_state.current_case['substances']) + 1 
                      if st.session_state.current_case['substances'] in COMMON_SUBSTANCES else 0,
                help="Select the primary substance involved"
            )
            
            # If "other" or custom substance, allow text input
            if not substances or substances not in COMMON_SUBSTANCES:
                substances = st.text_input(
                    "Custom Substance", 
                    value=st.session_state.current_case['substances'] if st.session_state.current_case['substances'] not in COMMON_SUBSTANCES else "",
                    placeholder="Enter substance name if not in list above"
                )
            
            severity = st.selectbox(
                "Severity Level",
                options=list(SEVERITY_LEVELS.keys()),
                index=list(SEVERITY_LEVELS.keys()).index(st.session_state.current_case['severity']),
                format_func=lambda x: f"{SEVERITY_LEVELS[x]['icon']} Level {SEVERITY_LEVELS[x]['level']}: {x}"
            )
            
            # Display severity description
            if severity:
                severity_info = SEVERITY_LEVELS[severity]
                st.markdown(f"**{render_severity_badge(severity)}**")
            
            col_ed, col_followup = st.columns(2)
            
            with col_ed:
                emergency_department_recommended = st.checkbox(
                    "🏥 ED Recommended",
                    value=st.session_state.current_case['emergency_department_recommended']
                )
            
            with col_followup:
                follow_up_required = st.checkbox(
                    "📅 Follow-up Required",
                    value=st.session_state.current_case['follow_up_required']
                )
            
            hpi = st.text_area(
                "History of Present Illness *",
                value=st.session_state.current_case['hpi'],
                height=100,
                placeholder="Describe the sequence of events, symptoms, and timeline..."
            )
            
            physical_exam = st.text_area(
                "Physical Examination",
                value=st.session_state.current_case['physical_exam'],
                height=80,
                placeholder="Document physical findings and vital signs..."
            )
            
            recommendations = st.text_area(
                "Recommendations *",
                value=st.session_state.current_case['recommendations'],
                height=100,
                placeholder="Treatment recommendations and disposition..."
            )
        
        # Update session state with form values
        st.session_state.current_case.update({
            'specialist_name': specialist_name,
            'call_date': call_date.strftime('%Y-%m-%d'),
            'call_time': call_time.strftime('%H:%M'),
            'first_name': first_name,
            'last_name': last_name,
            'dob': dob.strftime('%Y-%m-%d') if dob else '',
            'age': age,
            'substances': substances,
            'severity': severity,
            'emergency_department_recommended': emergency_department_recommended,
            'follow_up_required': follow_up_required,
            'hpi': hpi,
            'physical_exam': physical_exam,
            'recommendations': recommendations
        })
        
        # Action buttons
        col_save, col_new = st.columns(2)
        
        with col_save:
            if st.button("💾 Save Case", type="primary", use_container_width=True):
                # Validate case data
                errors = validate_case_data(st.session_state.current_case)
                
                if errors:
                    st.error("Please fix the following errors:")
                    for error in errors:
                        st.error(f"• {error}")
                else:
                    # Create PoisonCase object and save
                    case = PoisonCase(**st.session_state.current_case)
                    
                    if st.session_state.data_store.save_case(case):
                        st.success("✅ Case saved successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to save case. Please try again.")
        
        with col_new:
            if st.button("🆕 New Case", use_container_width=True):
                # Reset to new case
                now = datetime.datetime.now()
                st.session_state.current_case = {
                    'case_id': generate_case_id(),
                    'call_date': now.strftime('%Y-%m-%d'),
                    'call_time': now.strftime('%H:%M'),
                    'specialist_name': '',
                    'first_name': '',
                    'last_name': '',
                    'dob': '',
                    'age': 0,
                    'substances': '',
                    'hpi': '',
                    'physical_exam': '',
                    'recommendations': '',
                    'severity': 'MINIMAL',
                    'follow_up_required': False,
                    'emergency_department_recommended': False
                }
                st.session_state.transcript = ''
                st.success("📝 New case started!")
                st.rerun()

def render_case_management():
    """Render the case management interface"""
    
    st.subheader("📊 Case Management Dashboard")
    
    # Get all cases
    all_cases = st.session_state.data_store.get_cases()
    
    # Analytics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cases", len(all_cases))
    
    with col2:
        ed_cases = len([c for c in all_cases if c.emergency_department_recommended])
        st.metric("ED Recommended", ed_cases)
    
    with col3:
        followup_cases = len([c for c in all_cases if c.follow_up_required])
        st.metric("Follow-up Required", followup_cases)
    
    with col4:
        high_severity = len([c for c in all_cases if c.severity in ['MAJOR', 'FATAL']])
        st.metric("High Severity", high_severity)
    
    st.markdown("---")
    
    # Search and filter controls
    col_search, col_severity, col_export = st.columns([2, 1, 1])
    
    with col_search:
        search_term = st.text_input("🔍 Search Cases", placeholder="Search by ID, name, or substance...")
    
    with col_severity:
        severity_filter = st.selectbox(
            "Filter by Severity",
            options=["All"] + list(SEVERITY_LEVELS.keys())
        )
    
    with col_export:
        if st.button("📤 Export Data", use_container_width=True):
            # Export filtered cases to CSV
            filtered_cases = st.session_state.data_store.search_cases(search_term, severity_filter)
            
            if filtered_cases:
                # Convert to DataFrame
                case_dicts = [asdict(case) for case in filtered_cases]
                df = pd.DataFrame(case_dicts)
                
                # Convert to CSV
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                
                # Download button
                st.download_button(
                    label="💾 Download CSV",
                    data=csv_data,
                    file_name=f"poison_cases_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No cases to export")
    
    # Filter and display cases
    filtered_cases = st.session_state.data_store.search_cases(search_term, severity_filter)
    
    if not filtered_cases:
        if len(all_cases) == 0:
            st.info("📝 No cases created yet. Use the Data Entry tab to create your first case.")
        else:
            st.info("🔍 No cases match your search criteria.")
    else:
        st.markdown(f"**Found {len(filtered_cases)} case(s)**")
        
        # Display cases
        for case in filtered_cases:
            with st.expander(f"📋 {case.case_id} - {case.first_name} {case.last_name}", expanded=False):
                col_info, col_clinical = st.columns(2)
                
                with col_info:
                    st.markdown("**📞 Case Information**")
                    st.text(f"Specialist: {case.specialist_name}")
                    st.text(f"Date/Time: {case.call_date} {case.call_time}")
                    st.markdown(f"**Severity:** {render_severity_badge(case.severity)}")
                    
                    st.markdown("**👤 Patient Information**")
                    st.text(f"Name: {case.first_name} {case.last_name}")
                    st.text(f"Age: {case.age} years")
                    st.text(f"DOB: {case.dob}")
                    
                    st.markdown("**🏥 Disposition**")
                    st.text(f"ED Recommended: {'✅ Yes' if case.emergency_department_recommended else '❌ No'}")
                    st.text(f"Follow-up Required: {'✅ Yes' if case.follow_up_required else '❌ No'}")
                
                with col_clinical:
                    st.markdown("**💊 Substances Involved**")
                    st.text(case.substances)
                    
                    st.markdown("**📝 History of Present Illness**")
                    st.text(case.hpi)
                    
                    if case.physical_exam:
                        st.markdown("**🩺 Physical Examination**")
                        st.text(case.physical_exam)
                    
                    st.markdown("**💡 Recommendations**")
                    st.text(case.recommendations)
                    
                    if case.updates:
                        st.markdown("**📋 Case Updates**")
                        for i, update in enumerate(case.updates):
                            st.text(f"Update {i+1}: {update.get('text', 'No details')}")

if __name__ == "__main__":
    main()