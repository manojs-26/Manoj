import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
  Dimensions
} from 'react-native';
import { Audio } from 'expo-av';
import Slider from '@react-native-community/slider';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaView } from 'react-native-safe-area-context';

const { width, height } = Dimensions.get('window');
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

export default function MRINoiseMaskingApp() {
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
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Refs
  const scanTimer = useRef<NodeJS.Timeout | null>(null);
  const progressTimer = useRef<NodeJS.Timeout | null>(null);

  // Initialize audio mode
  useEffect(() => {
    Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      staysActiveInBackground: true,
      playsInSilentModeIOS: true,
      shouldDuckAndroid: false,
      playThroughEarpieceAndroid: false,
    });

    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      if (scanTimer.current) {
        clearInterval(scanTimer.current);
      }
      if (progressTimer.current) {
        clearInterval(progressTimer.current);
      }
    };
  }, []);

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
      Alert.alert('Error', 'Failed to load MRI patterns and sound profiles');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAudioFile = async (soundProfile: SoundProfile) => {
    try {
      if (sound) {
        await sound.unloadAsync();
      }

      // In a real app, you'd load actual audio files
      // For demo, we'll use a generated tone or placeholder
      // This would need actual audio files in assets
      const audioUri = `https://www.soundjay.com/misc/sounds-for-games/beep-07a.wav`; // Placeholder
      
      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: audioUri },
        { 
          shouldPlay: false, 
          volume: volume,
          isLooping: true,
        }
      );
      
      setSound(newSound);
      return true;
    } catch (error) {
      console.error('Error loading audio:', error);
      // Fallback: continue without audio for demo
      return false;
    }
  };

  const startSession = async () => {
    if (!selectedMRIPattern || !selectedSoundProfile) {
      Alert.alert('Selection Required', 'Please select both MRI pattern and sound profile');
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
      
      setIsPlaying(true);
      
    } catch (error) {
      console.error('Error starting session:', error);
      Alert.alert('Error', 'Failed to start masking session');
    } finally {
      setIsLoading(false);
    }
  };

  const stopSession = async () => {
    try {
      if (sound) {
        await sound.stopAsync();
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
          
          if (sound) {
            sound.setVolumeAsync(adjustedVolume);
          }
        }
      }
      
      // Auto-stop when complete
      if (currentTime >= totalDuration) {
        stopSession();
      }
    }, 1000);
  };

  const adjustVolume = async (newVolume: number) => {
    setVolume(newVolume);
    if (sound && isPlaying) {
      await sound.setVolumeAsync(newVolume);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderMRIPatternSelector = () => (
    <View style={styles.sectionContainer}>
      <Text style={styles.sectionTitle}>Select MRI Scan Type</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
        {mriPatterns.map((pattern) => (
          <TouchableOpacity
            key={pattern.id}
            style={[
              styles.selectionCard,
              selectedMRIPattern?.id === pattern.id && styles.selectedCard
            ]}
            onPress={() => setSelectedMRIPattern(pattern)}
          >
            <Text style={styles.cardTitle}>{pattern.name}</Text>
            <Text style={styles.cardSubtitle}>{pattern.duration_minutes} min</Text>
            <Text style={styles.cardDetail}>{pattern.noise_frequency_hz} Hz</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderSoundProfileSelector = () => (
    <View style={styles.sectionContainer}>
      <Text style={styles.sectionTitle}>Select Masking Sound</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
        {soundProfiles.map((profile) => (
          <TouchableOpacity
            key={profile.id}
            style={[
              styles.selectionCard,
              selectedSoundProfile?.id === profile.id && styles.selectedCard
            ]}
            onPress={() => setSelectedSoundProfile(profile)}
          >
            <Text style={styles.cardTitle}>{profile.name}</Text>
            <Text style={styles.cardSubtitle}>{profile.type}</Text>
            <Text style={styles.cardDetail}>{profile.base_frequency_hz} Hz</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderControls = () => (
    <View style={styles.controlsContainer}>
      <View style={styles.volumeControl}>
        <Text style={styles.controlLabel}>Volume</Text>
        <View style={styles.sliderContainer}>
          <Ionicons name="volume-low" size={20} color="#666" />
          <Slider
            style={styles.slider}
            value={volume}
            onValueChange={adjustVolume}
            minimumValue={0}
            maximumValue={1}
            minimumTrackTintColor="#007AFF"
            maximumTrackTintColor="#E0E0E0"
            thumbStyle={styles.sliderThumb}
            disabled={isPlaying}
          />
          <Ionicons name="volume-high" size={20} color="#666" />
        </View>
        <Text style={styles.volumeValue}>{Math.round(volume * 100)}%</Text>
      </View>

      <TouchableOpacity
        style={[styles.mainButton, isPlaying ? styles.stopButton : styles.startButton]}
        onPress={isPlaying ? stopSession : startSession}
        disabled={isLoading || (!selectedMRIPattern || !selectedSoundProfile)}
      >
        <Ionicons 
          name={isPlaying ? "stop" : "play"} 
          size={32} 
          color="white" 
          style={styles.buttonIcon}
        />
        <Text style={styles.mainButtonText}>
          {isLoading ? 'Loading...' : isPlaying ? 'Stop Session' : 'Start Masking'}
        </Text>
      </TouchableOpacity>
    </View>
  );

  const renderProgress = () => {
    if (!isPlaying) return null;

    return (
      <View style={styles.progressContainer}>
        <Text style={styles.progressTitle}>Scan Progress</Text>
        
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${scanProgress}%` }]} />
        </View>
        
        <View style={styles.progressDetails}>
          <Text style={styles.timeRemaining}>
            Time Remaining: {formatTime(timeRemaining)}
          </Text>
          <Text style={styles.currentPhase}>{currentPhase}</Text>
        </View>
        
        <Text style={styles.progressPercent}>{Math.round(scanProgress)}% Complete</Text>
      </View>
    );
  };

  if (isLoading && mriPatterns.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading MRI Masking System...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>MRI Noise Masking</Text>
          <Text style={styles.subtitle}>Adaptive Soundscape System</Text>
        </View>

        {!isPlaying && (
          <>
            {renderMRIPatternSelector()}
            {renderSoundProfileSelector()}
          </>
        )}

        {renderProgress()}
        {renderControls()}

        {selectedMRIPattern && selectedSoundProfile && !isPlaying && (
          <View style={styles.infoContainer}>
            <Text style={styles.infoTitle}>Session Preview</Text>
            <Text style={styles.infoText}>
              Scan: {selectedMRIPattern.name} ({selectedMRIPattern.duration_minutes} min)
            </Text>
            <Text style={styles.infoText}>
              Sound: {selectedSoundProfile.name} ({selectedSoundProfile.type})
            </Text>
            <Text style={styles.infoText}>
              Target Frequency: {selectedMRIPattern.noise_frequency_hz} Hz
            </Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 18,
    color: '#666',
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 5,
    textAlign: 'center',
  },
  sectionContainer: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 15,
  },
  horizontalScroll: {
    paddingVertical: 5,
  },
  selectionCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 15,
    marginRight: 15,
    minWidth: 140,
    borderWidth: 2,
    borderColor: '#E0E0E0',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  selectedCard: {
    borderColor: '#007AFF',
    backgroundColor: '#F0F8FF',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5,
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 3,
  },
  cardDetail: {
    fontSize: 12,
    color: '#999',
  },
  controlsContainer: {
    backgroundColor: 'white',
    borderRadius: 15,
    padding: 20,
    marginVertical: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  volumeControl: {
    marginBottom: 25,
  },
  controlLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  slider: {
    flex: 1,
    marginHorizontal: 15,
    height: 40,
  },
  sliderThumb: {
    backgroundColor: '#007AFF',
    width: 20,
    height: 20,
  },
  volumeValue: {
    textAlign: 'center',
    fontSize: 14,
    color: '#666',
  },
  mainButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 12,
    minHeight: 60,
  },
  startButton: {
    backgroundColor: '#007AFF',
  },
  stopButton: {
    backgroundColor: '#FF3B30',
  },
  buttonIcon: {
    marginRight: 10,
  },
  mainButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
  },
  progressContainer: {
    backgroundColor: 'white',
    borderRadius: 15,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  progressTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 15,
    textAlign: 'center',
  },
  progressBar: {
    height: 8,
    backgroundColor: '#E0E0E0',
    borderRadius: 4,
    marginBottom: 15,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
    borderRadius: 4,
  },
  progressDetails: {
    alignItems: 'center',
    marginBottom: 10,
  },
  timeRemaining: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginBottom: 5,
  },
  currentPhase: {
    fontSize: 14,
    color: '#666',
  },
  progressPercent: {
    fontSize: 14,
    color: '#007AFF',
    textAlign: 'center',
    fontWeight: '500',
  },
  infoContainer: {
    backgroundColor: '#F8F8F8',
    borderRadius: 12,
    padding: 15,
    marginTop: 10,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
});