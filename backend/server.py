from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# MRI Models
class MRIPattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    duration_minutes: int
    noise_frequency_hz: int
    noise_intensity_db: int
    sequence_pattern: List[Dict[str, int]]  # [{"frequency": 2000, "duration": 30, "intensity": 120}]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MRIPatternCreate(BaseModel):
    name: str
    duration_minutes: int
    noise_frequency_hz: int = 2000  # Default typical MRI frequency
    noise_intensity_db: int = 120   # Default MRI noise level
    sequence_pattern: Optional[List[Dict[str, int]]] = None

class SoundProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # "nature", "white_noise", "ambient", "music"
    base_frequency_hz: int
    masking_effectiveness: Dict[str, float]  # {"low_freq": 0.8, "mid_freq": 0.9, "high_freq": 0.7}
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SoundProfileCreate(BaseModel):
    name: str
    type: str
    base_frequency_hz: int
    masking_effectiveness: Dict[str, float]
    file_path: str

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mri_pattern_id: str
    sound_profile_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    comfort_rating: Optional[int] = None  # 1-10 scale
    volume_level: float = 0.7
    completed: bool = False

class UserSessionCreate(BaseModel):
    mri_pattern_id: str
    sound_profile_id: str
    volume_level: float = 0.7

# Initialize default MRI patterns and sound profiles
@api_router.on_event("startup")
async def startup_db():
    # Check if we have default MRI patterns
    existing_patterns = await db.mri_patterns.count_documents({})
    if existing_patterns == 0:
        default_patterns = [
            {
                "name": "Brain T1 Weighted",
                "duration_minutes": 15,
                "noise_frequency_hz": 2000,
                "noise_intensity_db": 120,
                "sequence_pattern": [
                    {"frequency": 2000, "duration": 300, "intensity": 120},
                    {"frequency": 1800, "duration": 180, "intensity": 115},
                    {"frequency": 2200, "duration": 420, "intensity": 125}
                ]
            },
            {
                "name": "Spine MRI",
                "duration_minutes": 25,
                "noise_frequency_hz": 1500,
                "noise_intensity_db": 118,
                "sequence_pattern": [
                    {"frequency": 1500, "duration": 600, "intensity": 118},
                    {"frequency": 1700, "duration": 300, "intensity": 120},
                    {"frequency": 1400, "duration": 600, "intensity": 115}
                ]
            },
            {
                "name": "Knee Joint",
                "duration_minutes": 10,
                "noise_frequency_hz": 2500,
                "noise_intensity_db": 122,
                "sequence_pattern": [
                    {"frequency": 2500, "duration": 200, "intensity": 122},
                    {"frequency": 2300, "duration": 150, "intensity": 118},
                    {"frequency": 2700, "duration": 250, "intensity": 125}
                ]
            }
        ]
        
        for pattern_data in default_patterns:
            pattern = MRIPattern(**pattern_data)
            await db.mri_patterns.insert_one(pattern.dict())
    
    # Check if we have default sound profiles
    existing_sounds = await db.sound_profiles.count_documents({})
    if existing_sounds == 0:
        default_sounds = [
            {
                "name": "Ocean Waves",
                "type": "nature",
                "base_frequency_hz": 500,
                "masking_effectiveness": {"low_freq": 0.9, "mid_freq": 0.8, "high_freq": 0.6},
                "file_path": "ocean_waves.mp3"
            },
            {
                "name": "Forest Rain",
                "type": "nature", 
                "base_frequency_hz": 800,
                "masking_effectiveness": {"low_freq": 0.7, "mid_freq": 0.9, "high_freq": 0.8},
                "file_path": "forest_rain.mp3"
            },
            {
                "name": "White Noise",
                "type": "white_noise",
                "base_frequency_hz": 1000,
                "masking_effectiveness": {"low_freq": 0.8, "mid_freq": 0.9, "high_freq": 0.9},
                "file_path": "white_noise.mp3"
            },
            {
                "name": "Pink Noise",
                "type": "white_noise",
                "base_frequency_hz": 750,
                "masking_effectiveness": {"low_freq": 0.9, "mid_freq": 0.8, "high_freq": 0.7},
                "file_path": "pink_noise.mp3"
            },
            {
                "name": "Ambient Meditation",
                "type": "ambient",
                "base_frequency_hz": 400,
                "masking_effectiveness": {"low_freq": 0.8, "mid_freq": 0.7, "high_freq": 0.5},
                "file_path": "ambient_meditation.mp3"
            }
        ]
        
        for sound_data in default_sounds:
            sound = SoundProfile(**sound_data)
            await db.sound_profiles.insert_one(sound.dict())

# MRI Pattern endpoints
@api_router.get("/mri-patterns", response_model=List[MRIPattern])
async def get_mri_patterns():
    """Get all available MRI scan patterns"""
    patterns = await db.mri_patterns.find().to_list(100)
    return [MRIPattern(**pattern) for pattern in patterns]

@api_router.get("/mri-patterns/{pattern_id}", response_model=MRIPattern)
async def get_mri_pattern(pattern_id: str):
    """Get specific MRI pattern by ID"""
    pattern = await db.mri_patterns.find_one({"id": pattern_id})
    if not pattern:
        raise HTTPException(status_code=404, detail="MRI pattern not found")
    return MRIPattern(**pattern)

@api_router.post("/mri-patterns", response_model=MRIPattern)
async def create_mri_pattern(pattern: MRIPatternCreate):
    """Create new MRI pattern"""
    if not pattern.sequence_pattern:
        # Generate default sequence pattern based on duration
        total_seconds = pattern.duration_minutes * 60
        pattern.sequence_pattern = [
            {"frequency": pattern.noise_frequency_hz, "duration": total_seconds, "intensity": pattern.noise_intensity_db}
        ]
    
    pattern_obj = MRIPattern(**pattern.dict())
    await db.mri_patterns.insert_one(pattern_obj.dict())
    return pattern_obj

# Sound Profile endpoints
@api_router.get("/sound-profiles", response_model=List[SoundProfile])
async def get_sound_profiles():
    """Get all available sound profiles"""
    profiles = await db.sound_profiles.find().to_list(100)
    return [SoundProfile(**profile) for profile in profiles]

@api_router.get("/sound-profiles/{profile_id}", response_model=SoundProfile)
async def get_sound_profile(profile_id: str):
    """Get specific sound profile by ID"""
    profile = await db.sound_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Sound profile not found")
    return SoundProfile(**profile)

@api_router.post("/sound-profiles", response_model=SoundProfile)
async def create_sound_profile(profile: SoundProfileCreate):
    """Create new sound profile"""
    profile_obj = SoundProfile(**profile.dict())
    await db.sound_profiles.insert_one(profile_obj.dict())
    return profile_obj

# User Session endpoints
@api_router.post("/sessions", response_model=UserSession)
async def create_session(session: UserSessionCreate):
    """Start a new MRI masking session"""
    # Verify MRI pattern and sound profile exist
    mri_pattern = await db.mri_patterns.find_one({"id": session.mri_pattern_id})
    sound_profile = await db.sound_profiles.find_one({"id": session.sound_profile_id})
    
    if not mri_pattern:
        raise HTTPException(status_code=400, detail="Invalid MRI pattern ID")
    if not sound_profile:
        raise HTTPException(status_code=400, detail="Invalid sound profile ID")
    
    session_obj = UserSession(**session.dict())
    await db.user_sessions.insert_one(session_obj.dict())
    return session_obj

@api_router.put("/sessions/{session_id}/complete")
async def complete_session(session_id: str, comfort_rating: Optional[int] = None):
    """Complete a session with optional comfort rating"""
    update_data = {
        "end_time": datetime.utcnow(),
        "completed": True
    }
    if comfort_rating is not None:
        if comfort_rating < 1 or comfort_rating > 10:
            raise HTTPException(status_code=400, detail="Comfort rating must be between 1 and 10")
        update_data["comfort_rating"] = comfort_rating
    
    result = await db.user_sessions.update_one(
        {"id": session_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session completed successfully"}

@api_router.get("/sessions/{session_id}", response_model=UserSession)
async def get_session(session_id: str):
    """Get session details"""
    session = await db.user_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return UserSession(**session)

# Masking effectiveness calculation
@api_router.get("/masking-effectiveness/{mri_pattern_id}/{sound_profile_id}")
async def calculate_masking_effectiveness(mri_pattern_id: str, sound_profile_id: str):
    """Calculate how effective a sound profile will be for masking a specific MRI pattern"""
    mri_pattern = await db.mri_patterns.find_one({"id": mri_pattern_id})
    sound_profile = await db.sound_profiles.find_one({"id": sound_profile_id})
    
    if not mri_pattern or not sound_profile:
        raise HTTPException(status_code=404, detail="Pattern or profile not found")
    
    mri_freq = mri_pattern["noise_frequency_hz"]
    sound_effectiveness = sound_profile["masking_effectiveness"]
    
    # Determine frequency range
    if mri_freq < 1000:
        effectiveness = sound_effectiveness["low_freq"]
    elif mri_freq < 3000:
        effectiveness = sound_effectiveness["mid_freq"]
    else:
        effectiveness = sound_effectiveness["high_freq"]
    
    return {
        "effectiveness_score": effectiveness,
        "mri_frequency": mri_freq,
        "sound_type": sound_profile["type"],
        "recommended_volume": min(1.0, effectiveness + 0.2)
    }

# Basic health check
@api_router.get("/")
async def root():
    return {"message": "MRI Noise Masking API", "status": "active"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()