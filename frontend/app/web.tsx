import React, { useState, useEffect, useRef } from 'react';
import './web.css';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface MRIPattern {
  id: string;
  name: string;
  duration_minutes: number;
  noise_frequency_hz: number;
  noise_intensity_db: number;
  sequence_pattern: Array<{
    frequency: number;
    duration: number;
    intensity: number;
  }>;
}

interface SoundProfile {
  id: string;
  name: string;
  type: string;
  base_frequency_hz: number;
  masking_effectiveness: {
    low_freq: number;
    mid_freq: number;
    high_freq: number;
  };
  file_path: string;
}

interface UserSession {
  id: string;
  mri_pattern_id: string;
  sound_profile_id: string;
  volume_level: number;
}

export default function MRINoiseMaskingWebApp() {
  // State management
  const [mriPatterns, setMriPatterns] = useState<MRIPattern[]>([]);
  const [soundProfiles, setSoundProfiles] = useState<SoundProfile[]>([]);
  const [selectedMRIPattern, setSelectedMRIPattern] = useState<MRIPattern | null>(null);
  const [selectedSoundProfile, setSelectedSoundProfile] = useState<SoundProfile | null>(null);
  const [currentSession, setCurrentSession] = useState<UserSession | null>(null);
  
  // Audio and timing state
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.7);
  const [scanProgress, setScanProgress] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [currentPhase, setCurrentPhase] = useState('');
  
  // Audio management
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Refs
  const scanTimer = useRef<NodeJS.Timeout | null>(null);
  const progressTimer = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audio) {
        audio.pause();
      }
      if (scanTimer.current) {
        clearInterval(scanTimer.current);
      }
      if (progressTimer.current) {
        clearInterval(progressTimer.current);
      }
    };
  }, [audio]);

  // Load data from API
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Load MRI patterns
      const mriResponse = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/mri-patterns`);
      const mriData = await mriResponse.json();
      setMriPatterns(mriData);
      
      // Load sound profiles
      const soundResponse = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/sound-profiles`);
      const soundData = await soundResponse.json();
      setSoundProfiles(soundData);
      
      // Set defaults
      if (mriData.length > 0) setSelectedMRIPattern(mriData[0]);
      if (soundData.length > 0) setSelectedSoundProfile(soundData[0]);
      
    } catch (error) {
      console.error('Error loading data:', error);
      alert('Failed to load MRI patterns and sound profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAudioFile = async (soundProfile: SoundProfile) => {
    try {
      if (audio) {
        audio.pause();
      }

      // Create audio context for white noise generation
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Generate white noise based on sound profile type
      let audioElement: HTMLAudioElement;
      
      if (soundProfile.type === 'white_noise' || soundProfile.type === 'nature') {
        // Generate synthetic audio for demo
        const buffer = audioContext.createBuffer(2, audioContext.sampleRate * 2, audioContext.sampleRate);
        
        for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
          const nowBuffering = buffer.getChannelData(channel);
          for (let i = 0; i < buffer.length; i++) {
            if (soundProfile.type === 'white_noise') {
              nowBuffering[i] = Math.random() * 2 - 1;
            } else {
              // Generate nature-like sounds with lower frequency variations
              nowBuffering[i] = (Math.random() * 2 - 1) * 0.3 * Math.sin(i / 1000);
            }
          }
        }
        
        // Convert buffer to audio element
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        
        const gainNode = audioContext.createGain();
        gainNode.gain.value = volume;
        
        source.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Create a dummy audio element for control
        audioElement = new Audio();
        audioElement.volume = volume;
        
        // Store the audio context for stopping later
        (audioElement as any).audioContext = audioContext;
        (audioElement as any).source = source;
        (audioElement as any).gainNode = gainNode;
        
        audioElement.play = () => {
          if (audioContext.state === 'suspended') {
            audioContext.resume();
          }
          source.start();
          return Promise.resolve();
        };
        
        audioElement.pause = () => {
          source.stop();
          audioContext.close();
        };
        
      } else {
        // For other sound types, use a placeholder or generate appropriate sounds
        audioElement = new Audio();
        audioElement.volume = volume;
        audioElement.loop = true;
      }
      
      setAudio(audioElement);
      return true;
    } catch (error) {
      console.error('Error loading audio:', error);
      // Continue without audio for demo
      return false;
    }
  };

  const startSession = async () => {
    if (!selectedMRIPattern || !selectedSoundProfile) {
      alert('Please select both MRI pattern and sound profile');
      return;
    }

    try {
      setIsLoading(true);
      
      // Create session
      const sessionResponse = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mri_pattern_id: selectedMRIPattern.id,
          sound_profile_id: selectedSoundProfile.id,
          volume_level: volume,
        }),
      });
      
      const sessionData = await sessionResponse.json();
      setCurrentSession(sessionData);
      
      // Load and start audio
      await loadAudioFile(selectedSoundProfile);
      
      // Start MRI simulation
      startMRISimulation();
      
      if (audio) {
        audio.play();
      }
      
      setIsPlaying(true);
      
    } catch (error) {
      console.error('Error starting session:', error);
      alert('Failed to start masking session');
    } finally {
      setIsLoading(false);
    }
  };

  const stopSession = async () => {
    try {
      if (audio) {
        audio.pause();
      }
      
      if (scanTimer.current) {
        clearInterval(scanTimer.current);
      }
      
      if (progressTimer.current) {
        clearInterval(progressTimer.current);
      }
      
      if (currentSession) {
        // Complete session in backend
        await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/sessions/${currentSession.id}/complete`, {
          method: 'PUT',
        });
      }
      
      setIsPlaying(false);
      setScanProgress(0);
      setTimeRemaining(0);
      setCurrentPhase('');
      setCurrentSession(null);
      
    } catch (error) {
      console.error('Error stopping session:', error);
    }
  };

  const startMRISimulation = () => {
    if (!selectedMRIPattern) return;
    
    const totalDuration = selectedMRIPattern.duration_minutes * 60; // Convert to seconds
    const sequences = selectedMRIPattern.sequence_pattern;
    
    setTimeRemaining(totalDuration);
    setScanProgress(0);
    
    let currentTime = 0;
    let sequenceIndex = 0;
    let sequenceStartTime = 0;
    
    // Progress timer - updates every second
    progressTimer.current = setInterval(() => {
      currentTime += 1;
      const progress = (currentTime / totalDuration) * 100;
      setScanProgress(Math.min(progress, 100));
      setTimeRemaining(Math.max(totalDuration - currentTime, 0));
      
      // Update current phase based on sequence
      if (sequences && sequences.length > 0) {
        const currentSequence = sequences[sequenceIndex];
        if (currentSequence) {
          const sequenceElapsed = currentTime - sequenceStartTime;
          if (sequenceElapsed >= currentSequence.duration && sequenceIndex < sequences.length - 1) {
            sequenceIndex++;
            sequenceStartTime = currentTime;
          }
          
          const phaseName = `Phase ${sequenceIndex + 1}: ${currentSequence.frequency}Hz`;
          setCurrentPhase(phaseName);
          
          // Adjust audio volume based on MRI intensity (simulated)
          const intensityFactor = currentSequence.intensity / 120; // Normalize to max expected dB
          const adjustedVolume = Math.min(volume * intensityFactor, 1.0);
          
          if (audio && (audio as any).gainNode) {
            (audio as any).gainNode.gain.value = adjustedVolume;
          } else if (audio) {
            audio.volume = adjustedVolume;
          }
        }
      }
      
      // Auto-stop when complete
      if (currentTime >= totalDuration) {
        stopSession();
      }
    }, 1000);
  };

  const adjustVolume = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(event.target.value);
    setVolume(newVolume);
    if (audio && isPlaying) {
      if ((audio as any).gainNode) {
        (audio as any).gainNode.gain.value = newVolume;
      } else {
        audio.volume = newVolume;
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (isLoading && mriPatterns.length === 0) {
    return (
      <div className="container loading-container">
        <div className="loading-text">Loading MRI Masking System...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">MRI Noise Masking</h1>
        <p className="subtitle">Adaptive Soundscape System</p>
      </div>

      {!isPlaying && (
        <>
          <div className="section-container">
            <h2 className="section-title">Select MRI Scan Type</h2>
            <div className="horizontal-scroll">
              {mriPatterns.map((pattern) => (
                <div
                  key={pattern.id}
                  className={`selection-card ${selectedMRIPattern?.id === pattern.id ? 'selected' : ''}`}
                  onClick={() => setSelectedMRIPattern(pattern)}
                >
                  <div className="card-title">{pattern.name}</div>
                  <div className="card-subtitle">{pattern.duration_minutes} min</div>
                  <div className="card-detail">{pattern.noise_frequency_hz} Hz</div>
                </div>
              ))}
            </div>
          </div>

          <div className="section-container">
            <h2 className="section-title">Select Masking Sound</h2>
            <div className="horizontal-scroll">
              {soundProfiles.map((profile) => (
                <div
                  key={profile.id}
                  className={`selection-card ${selectedSoundProfile?.id === profile.id ? 'selected' : ''}`}
                  onClick={() => setSelectedSoundProfile(profile)}
                >
                  <div className="card-title">{profile.name}</div>
                  <div className="card-subtitle">{profile.type}</div>
                  <div className="card-detail">{profile.base_frequency_hz} Hz</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {isPlaying && (
        <div className="progress-container">
          <h2 className="progress-title">Scan Progress</h2>
          
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${scanProgress}%` }} />
          </div>
          
          <div className="progress-details">
            <div className="time-remaining">
              Time Remaining: {formatTime(timeRemaining)}
            </div>
            <div className="current-phase">{currentPhase}</div>
          </div>
          
          <div className="progress-percent">{Math.round(scanProgress)}% Complete</div>
        </div>
      )}

      <div className="controls-container">
        <div className="volume-control">
          <label className="control-label">Volume</label>
          <div className="slider-container">
            <span className="volume-icon">🔉</span>
            <input
              type="range"
              className="slider"
              value={volume}
              onChange={adjustVolume}
              min="0"
              max="1"
              step="0.01"
              disabled={isPlaying}
            />
            <span className="volume-icon">🔊</span>
          </div>
          <div className="volume-value">{Math.round(volume * 100)}%</div>
        </div>

        <button
          className={`main-button ${isPlaying ? 'stop-button' : 'start-button'}`}
          onClick={isPlaying ? stopSession : startSession}
          disabled={isLoading || (!selectedMRIPattern || !selectedSoundProfile)}
        >
          <span className="button-icon">{isPlaying ? '⏹️' : '▶️'}</span>
          {isLoading ? 'Loading...' : isPlaying ? 'Stop Session' : 'Start Masking'}
        </button>
      </div>

      {selectedMRIPattern && selectedSoundProfile && !isPlaying && (
        <div className="info-container">
          <h3 className="info-title">Session Preview</h3>
          <div className="info-text">
            Scan: {selectedMRIPattern.name} ({selectedMRIPattern.duration_minutes} min)
          </div>
          <div className="info-text">
            Sound: {selectedSoundProfile.name} ({selectedSoundProfile.type})
          </div>
          <div className="info-text">
            Target Frequency: {selectedMRIPattern.noise_frequency_hz} Hz
          </div>
        </div>
      )}
    </div>
  );
}