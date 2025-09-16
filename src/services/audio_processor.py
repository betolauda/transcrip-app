"""
Advanced audio processing service with optimization features.

This module provides enhanced audio processing capabilities including:
- Audio format conversion and validation
- Quality analysis and enhancement
- Noise reduction and normalization
- Chunked processing for large files
- Background processing with progress tracking
- Audio metadata extraction
"""
import os
import logging
import hashlib
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import threading
import queue
import time

# Audio processing libraries
try:
    import librosa
    import soundfile as sf
    import noisereduce as nr
    import numpy as np
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    logging.warning("Advanced audio processing libraries not available. Install: pip install librosa soundfile noisereduce")

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Audio file metadata."""
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    bitrate: Optional[int] = None
    file_size_bytes: int = 0
    quality_score: float = 0.0
    noise_level: float = 0.0
    speech_probability: float = 0.0


@dataclass
class ProcessingProgress:
    """Audio processing progress tracking."""
    total_chunks: int
    processed_chunks: int
    current_stage: str
    estimated_time_remaining: float
    started_at: datetime
    errors: List[str]

    @property
    def progress_percentage(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100


@dataclass
class AudioProcessingResult:
    """Result of audio processing operations."""
    success: bool
    original_file: Path
    processed_file: Optional[Path] = None
    metadata: Optional[AudioMetadata] = None
    processing_time_seconds: float = 0.0
    quality_improvements: Dict[str, float] = None
    error_message: Optional[str] = None
    chunks_processed: int = 0

    def __post_init__(self):
        if self.quality_improvements is None:
            self.quality_improvements = {}


class AudioQualityAnalyzer:
    """Analyzes and improves audio quality."""

    def __init__(self):
        self.target_sample_rate = 16000  # Optimal for Whisper
        self.target_channels = 1  # Mono for speech recognition

    def analyze_quality(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Analyze audio quality metrics."""
        try:
            # Calculate RMS energy (volume level)
            rms_energy = np.sqrt(np.mean(audio_data ** 2))

            # Calculate zero crossing rate (speech indicator)
            zero_crossings = np.sum(np.diff(np.signbit(audio_data)))
            zcr = zero_crossings / len(audio_data)

            # Calculate spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)[0]
            avg_spectral_centroid = np.mean(spectral_centroid)

            # Estimate noise level
            noise_level = self._estimate_noise_level(audio_data)

            # Speech probability estimation
            speech_prob = self._estimate_speech_probability(audio_data, sample_rate)

            # Overall quality score (0-1)
            quality_score = self._calculate_quality_score(
                rms_energy, zcr, avg_spectral_centroid, noise_level, speech_prob
            )

            return {
                "rms_energy": float(rms_energy),
                "zero_crossing_rate": float(zcr),
                "spectral_centroid": float(avg_spectral_centroid),
                "noise_level": float(noise_level),
                "speech_probability": float(speech_prob),
                "quality_score": float(quality_score)
            }

        except Exception as e:
            logger.error(f"Error analyzing audio quality: {e}")
            return {
                "rms_energy": 0.0,
                "zero_crossing_rate": 0.0,
                "spectral_centroid": 0.0,
                "noise_level": 1.0,
                "speech_probability": 0.0,
                "quality_score": 0.0
            }

    def _estimate_noise_level(self, audio_data: np.ndarray) -> float:
        """Estimate background noise level."""
        # Use the quietest 10% of the audio to estimate noise floor
        sorted_magnitudes = np.sort(np.abs(audio_data))
        noise_floor_index = int(len(sorted_magnitudes) * 0.1)
        noise_level = np.mean(sorted_magnitudes[:noise_floor_index])
        return min(noise_level * 10, 1.0)  # Normalize to 0-1

    def _estimate_speech_probability(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Estimate probability that audio contains speech."""
        try:
            # Calculate spectral features that indicate speech
            mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13)

            # Speech typically has certain MFCC patterns
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)

            # Simple heuristic based on MFCC characteristics
            # Real implementation would use a trained classifier
            speech_indicators = [
                mfcc_mean[1] > -20,  # Second MFCC coefficient
                mfcc_std[1] > 2,     # Variation in second coefficient
                np.mean(mfcc_mean[2:5]) > -15  # Mid-frequency content
            ]

            return sum(speech_indicators) / len(speech_indicators)

        except Exception:
            return 0.5  # Default neutral probability

    def _calculate_quality_score(self, rms_energy: float, zcr: float,
                                spectral_centroid: float, noise_level: float,
                                speech_prob: float) -> float:
        """Calculate overall quality score."""
        # Normalize and weight different factors
        energy_score = min(rms_energy * 10, 1.0)  # Good energy level
        zcr_score = min(zcr * 1000, 1.0)  # Appropriate zero crossing rate
        brightness_score = min(spectral_centroid / 4000, 1.0)  # Good frequency content
        noise_score = 1.0 - noise_level  # Low noise is good

        # Weighted combination
        quality = (
            energy_score * 0.3 +
            zcr_score * 0.2 +
            brightness_score * 0.2 +
            noise_score * 0.2 +
            speech_prob * 0.1
        )

        return min(quality, 1.0)


class AudioEnhancer:
    """Enhances audio quality for better transcription."""

    def __init__(self):
        self.target_sample_rate = 16000
        self.target_channels = 1

    def enhance_audio(self, audio_data: np.ndarray, sample_rate: int,
                     progress_callback: Optional[callable] = None) -> Tuple[np.ndarray, Dict[str, float]]:
        """Enhance audio quality through various processing steps."""
        if not AUDIO_LIBS_AVAILABLE:
            return audio_data, {}

        enhancements = {}
        enhanced_audio = audio_data.copy()

        try:
            # Step 1: Normalize volume
            if progress_callback:
                progress_callback("Normalizing volume")

            original_rms = np.sqrt(np.mean(enhanced_audio ** 2))
            enhanced_audio = self._normalize_volume(enhanced_audio)
            new_rms = np.sqrt(np.mean(enhanced_audio ** 2))
            enhancements["volume_normalization"] = abs(new_rms - original_rms)

            # Step 2: Noise reduction
            if progress_callback:
                progress_callback("Reducing noise")

            noise_before = self._estimate_noise_level(enhanced_audio)
            enhanced_audio = self._reduce_noise(enhanced_audio, sample_rate)
            noise_after = self._estimate_noise_level(enhanced_audio)
            enhancements["noise_reduction"] = max(0, noise_before - noise_after)

            # Step 3: Resample to optimal rate
            if progress_callback:
                progress_callback("Resampling audio")

            if sample_rate != self.target_sample_rate:
                enhanced_audio = librosa.resample(
                    enhanced_audio,
                    orig_sr=sample_rate,
                    target_sr=self.target_sample_rate
                )
                enhancements["resampling"] = abs(sample_rate - self.target_sample_rate) / sample_rate

            # Step 4: Convert to mono if stereo
            if progress_callback:
                progress_callback("Converting to mono")

            if len(enhanced_audio.shape) > 1:
                enhanced_audio = librosa.to_mono(enhanced_audio)
                enhancements["mono_conversion"] = 1.0

            # Step 5: Apply high-pass filter to remove low-frequency noise
            if progress_callback:
                progress_callback("Applying filters")

            enhanced_audio = self._apply_highpass_filter(enhanced_audio, self.target_sample_rate)
            enhancements["highpass_filter"] = 0.1  # Small improvement indicator

            return enhanced_audio, enhancements

        except Exception as e:
            logger.error(f"Error enhancing audio: {e}")
            return audio_data, {}

    def _normalize_volume(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio volume to optimal level."""
        # Target RMS level for speech (around -20 dB)
        target_rms = 0.1
        current_rms = np.sqrt(np.mean(audio_data ** 2))

        if current_rms > 0:
            scaling_factor = target_rms / current_rms
            # Prevent clipping
            scaling_factor = min(scaling_factor, 1.0 / np.max(np.abs(audio_data)))
            return audio_data * scaling_factor

        return audio_data

    def _reduce_noise(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply noise reduction."""
        try:
            # Use noisereduce library for spectral gating noise reduction
            reduced_noise = nr.reduce_noise(y=audio_data, sr=sample_rate)
            return reduced_noise
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return audio_data

    def _apply_highpass_filter(self, audio_data: np.ndarray, sample_rate: int,
                              cutoff_freq: float = 80.0) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise."""
        try:
            # Simple high-pass filter using librosa
            filtered_audio = librosa.effects.preemphasis(audio_data)
            return filtered_audio
        except Exception as e:
            logger.warning(f"High-pass filter failed: {e}")
            return audio_data

    def _estimate_noise_level(self, audio_data: np.ndarray) -> float:
        """Estimate noise level for comparison."""
        sorted_magnitudes = np.sort(np.abs(audio_data))
        noise_floor_index = int(len(sorted_magnitudes) * 0.1)
        return np.mean(sorted_magnitudes[:noise_floor_index])


class ChunkedAudioProcessor:
    """Process large audio files in chunks for memory efficiency."""

    def __init__(self, chunk_duration: float = 30.0):
        self.chunk_duration = chunk_duration  # seconds
        self.overlap_duration = 2.0  # seconds of overlap between chunks

    def process_large_file(self, file_path: Path,
                          progress_callback: Optional[callable] = None) -> AudioProcessingResult:
        """Process large audio file in chunks."""
        try:
            # Get audio info without loading entire file
            info = sf.info(str(file_path))
            total_duration = info.duration
            sample_rate = info.samplerate

            # Calculate number of chunks
            chunk_samples = int(self.chunk_duration * sample_rate)
            overlap_samples = int(self.overlap_duration * sample_rate)
            total_samples = int(total_duration * sample_rate)

            num_chunks = max(1, int(np.ceil(total_samples / chunk_samples)))

            if progress_callback:
                progress_callback(f"Processing {num_chunks} chunks")

            # Create temporary file for processed audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            processed_chunks = []
            start_time = time.time()

            # Process each chunk
            for chunk_idx in range(num_chunks):
                start_sample = chunk_idx * chunk_samples

                # Add overlap except for first chunk
                if chunk_idx > 0:
                    start_sample -= overlap_samples

                # Read chunk
                chunk_data, _ = librosa.load(
                    str(file_path),
                    sr=sample_rate,
                    offset=start_sample / sample_rate,
                    duration=self.chunk_duration + (self.overlap_duration if chunk_idx > 0 else 0)
                )

                # Enhance chunk
                enhancer = AudioEnhancer()
                enhanced_chunk, _ = enhancer.enhance_audio(chunk_data, sample_rate)
                processed_chunks.append(enhanced_chunk)

                if progress_callback:
                    progress = (chunk_idx + 1) / num_chunks * 100
                    progress_callback(f"Processed chunk {chunk_idx + 1}/{num_chunks} ({progress:.1f}%)")

            # Concatenate all chunks
            if processed_chunks:
                # Handle overlaps by cross-fading
                final_audio = self._concatenate_with_crossfade(processed_chunks, overlap_samples)

                # Save processed audio
                sf.write(str(temp_path), final_audio, sample_rate)

                # Create metadata
                metadata = AudioMetadata(
                    duration_seconds=len(final_audio) / sample_rate,
                    sample_rate=sample_rate,
                    channels=1,
                    format="wav",
                    file_size_bytes=temp_path.stat().st_size
                )

                processing_time = time.time() - start_time

                return AudioProcessingResult(
                    success=True,
                    original_file=file_path,
                    processed_file=temp_path,
                    metadata=metadata,
                    processing_time_seconds=processing_time,
                    chunks_processed=num_chunks
                )

        except Exception as e:
            logger.error(f"Error processing large file {file_path}: {e}")
            return AudioProcessingResult(
                success=False,
                original_file=file_path,
                error_message=str(e)
            )

    def _concatenate_with_crossfade(self, chunks: List[np.ndarray],
                                   overlap_samples: int) -> np.ndarray:
        """Concatenate audio chunks with crossfading at overlaps."""
        if not chunks:
            return np.array([])

        if len(chunks) == 1:
            return chunks[0]

        result = chunks[0]

        for chunk in chunks[1:]:
            if overlap_samples > 0 and len(result) >= overlap_samples:
                # Create crossfade
                fade_out = np.linspace(1, 0, overlap_samples)
                fade_in = np.linspace(0, 1, overlap_samples)

                # Apply crossfade to overlap region
                result[-overlap_samples:] *= fade_out
                result[-overlap_samples:] += chunk[:overlap_samples] * fade_in

                # Append the rest of the chunk
                result = np.concatenate([result, chunk[overlap_samples:]])
            else:
                # No overlap, just concatenate
                result = np.concatenate([result, chunk])

        return result


class OptimizedAudioProcessor:
    """Main audio processing service with optimizations."""

    def __init__(self):
        self.quality_analyzer = AudioQualityAnalyzer()
        self.enhancer = AudioEnhancer()
        self.chunked_processor = ChunkedAudioProcessor()
        self.processing_queue = queue.Queue()
        self.active_processes = {}
        self._setup_background_worker()

    def _setup_background_worker(self):
        """Setup background worker for processing queue."""
        def worker():
            while True:
                try:
                    task = self.processing_queue.get(timeout=1)
                    if task is None:  # Shutdown signal
                        break

                    task_id, file_path, options = task
                    result = self._process_audio_sync(file_path, options)
                    self.active_processes[task_id] = result

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Background worker error: {e}")

        # Start background worker thread
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def analyze_audio_file(self, file_path: Path) -> AudioMetadata:
        """Analyze audio file and extract metadata."""
        try:
            # Get basic file info
            file_stats = file_path.stat()

            if AUDIO_LIBS_AVAILABLE:
                # Load audio for analysis
                audio_data, sample_rate = librosa.load(str(file_path), sr=None)

                # Analyze quality
                quality_metrics = self.quality_analyzer.analyze_quality(audio_data, sample_rate)

                # Get audio info
                info = sf.info(str(file_path))

                return AudioMetadata(
                    duration_seconds=info.duration,
                    sample_rate=info.samplerate,
                    channels=info.channels,
                    format=info.format,
                    file_size_bytes=file_stats.st_size,
                    quality_score=quality_metrics.get("quality_score", 0.0),
                    noise_level=quality_metrics.get("noise_level", 0.0),
                    speech_probability=quality_metrics.get("speech_probability", 0.0)
                )
            else:
                # Basic metadata without advanced analysis
                return AudioMetadata(
                    duration_seconds=0.0,
                    sample_rate=0,
                    channels=0,
                    format="unknown",
                    file_size_bytes=file_stats.st_size
                )

        except Exception as e:
            logger.error(f"Error analyzing audio file {file_path}: {e}")
            return AudioMetadata(
                duration_seconds=0.0,
                sample_rate=0,
                channels=0,
                format="error",
                file_size_bytes=0
            )

    def process_audio_async(self, file_path: Path,
                           enhance_quality: bool = True,
                           chunk_large_files: bool = True) -> str:
        """Start asynchronous audio processing."""
        task_id = hashlib.md5(f"{file_path}_{time.time()}".encode()).hexdigest()

        options = {
            "enhance_quality": enhance_quality,
            "chunk_large_files": chunk_large_files
        }

        self.processing_queue.put((task_id, file_path, options))
        return task_id

    def get_processing_status(self, task_id: str) -> Optional[AudioProcessingResult]:
        """Get status of async processing task."""
        return self.active_processes.get(task_id)

    def process_audio_sync(self, file_path: Path,
                          enhance_quality: bool = True,
                          chunk_large_files: bool = True) -> AudioProcessingResult:
        """Process audio file synchronously."""
        return self._process_audio_sync(file_path, {
            "enhance_quality": enhance_quality,
            "chunk_large_files": chunk_large_files
        })

    def _process_audio_sync(self, file_path: Path, options: Dict[str, Any]) -> AudioProcessingResult:
        """Internal synchronous processing method."""
        start_time = time.time()

        try:
            # Analyze input file
            metadata = self.analyze_audio_file(file_path)

            # Determine processing strategy
            if options.get("chunk_large_files", True) and metadata.duration_seconds > 60:
                # Use chunked processing for large files
                result = self.chunked_processor.process_large_file(file_path)
                result.processing_time_seconds = time.time() - start_time
                return result

            elif options.get("enhance_quality", True) and AUDIO_LIBS_AVAILABLE:
                # Load and enhance audio
                audio_data, sample_rate = librosa.load(str(file_path), sr=None)

                enhanced_audio, enhancements = self.enhancer.enhance_audio(
                    audio_data, sample_rate
                )

                # Save enhanced audio
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = Path(temp_file.name)

                sf.write(str(temp_path), enhanced_audio, self.enhancer.target_sample_rate)

                # Update metadata
                enhanced_metadata = AudioMetadata(
                    duration_seconds=len(enhanced_audio) / self.enhancer.target_sample_rate,
                    sample_rate=self.enhancer.target_sample_rate,
                    channels=1,
                    format="wav",
                    file_size_bytes=temp_path.stat().st_size
                )

                return AudioProcessingResult(
                    success=True,
                    original_file=file_path,
                    processed_file=temp_path,
                    metadata=enhanced_metadata,
                    processing_time_seconds=time.time() - start_time,
                    quality_improvements=enhancements
                )

            else:
                # No processing needed, return original file
                return AudioProcessingResult(
                    success=True,
                    original_file=file_path,
                    processed_file=file_path,
                    metadata=metadata,
                    processing_time_seconds=time.time() - start_time
                )

        except Exception as e:
            logger.error(f"Error processing audio file {file_path}: {e}")
            return AudioProcessingResult(
                success=False,
                original_file=file_path,
                error_message=str(e),
                processing_time_seconds=time.time() - start_time
            )

    def cleanup_processed_files(self, max_age_hours: int = 24):
        """Clean up old processed files."""
        try:
            temp_dir = Path(tempfile.gettempdir())
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for temp_file in temp_dir.glob("tmp*.wav"):
                if current_time - temp_file.stat().st_mtime > max_age_seconds:
                    try:
                        temp_file.unlink()
                        logger.debug(f"Cleaned up old processed file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {temp_file}: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_optimization_recommendations(self, metadata: AudioMetadata) -> List[str]:
        """Get recommendations for optimizing audio quality."""
        recommendations = []

        if metadata.quality_score < 0.3:
            recommendations.append("Audio quality is poor. Consider using a better recording setup.")

        if metadata.noise_level > 0.5:
            recommendations.append("High noise level detected. Enable noise reduction.")

        if metadata.speech_probability < 0.4:
            recommendations.append("Low speech probability. Verify this is a speech recording.")

        if metadata.sample_rate > 48000:
            recommendations.append("High sample rate detected. Consider downsampling for efficiency.")

        if metadata.channels > 1:
            recommendations.append("Stereo audio detected. Mono conversion recommended for speech.")

        if metadata.duration_seconds > 300:
            recommendations.append("Long audio file. Consider using chunked processing.")

        return recommendations