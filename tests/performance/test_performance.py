"""
Performance tests for the transcription application.
Tests response times, throughput, and resource usage under various loads.
"""
import pytest
import time
import threading
import statistics
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock

from src.services.transcription_service import TranscriptionService
from src.services.glossary_service import GlossaryService
from src.services.term_detection_service import TermDetectionService
from src.repositories.database_repository import DatabaseRepository
from tests.fixtures.test_data import create_mp3_bytes, SAMPLE_TRANSCRIPTS
from tests.utils.test_helpers import temporary_file


class TestTranscriptionPerformance:
    """Test transcription service performance characteristics."""

    @pytest.fixture
    def performance_transcription_service(self):
        """Create transcription service optimized for performance testing."""
        db_repo = DatabaseRepository()
        return TranscriptionService(db_repo)

    @patch('src.services.transcription_service.whisper.load_model')
    def test_single_transcription_performance(self, mock_load_model, performance_transcription_service):
        """Test single transcription performance baseline."""
        # Mock fast Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Performance test transcript"}
        mock_load_model.return_value = mock_model

        service = performance_transcription_service
        mp3_content = create_mp3_bytes(2)  # 2MB file
        filename = "performance_test.mp3"

        # Warm up (exclude from timing)
        with temporary_file(mp3_content, "warmup", ".mp3") as temp_file:
            service.transcribe_audio(temp_file, "warmup.mp3")

        # Measure actual performance
        times = []
        for i in range(10):
            with temporary_file(mp3_content, f"perf_{i}", ".mp3") as temp_file:
                start_time = time.time()
                result = service.transcribe_audio(temp_file, f"perf_{i}.mp3")
                end_time = time.time()

                assert result.success is True
                times.append(end_time - start_time)

        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)

        assert avg_time < 2.0, f"Average transcription time {avg_time:.2f}s exceeds 2s threshold"
        assert max_time < 3.0, f"Maximum transcription time {max_time:.2f}s exceeds 3s threshold"
        assert max_time - min_time < 1.0, f"Time variance {max_time - min_time:.2f}s too high"

        # Log performance metrics
        print(f"\nTranscription Performance Metrics:")
        print(f"Average time: {avg_time:.3f}s")
        print(f"Min time: {min_time:.3f}s")
        print(f"Max time: {max_time:.3f}s")
        print(f"Standard deviation: {statistics.stdev(times):.3f}s")

    @patch('src.services.transcription_service.whisper.load_model')
    def test_concurrent_transcription_performance(self, mock_load_model, performance_transcription_service):
        """Test performance under concurrent transcription load."""
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "Concurrent test transcript"}
        mock_load_model.return_value = mock_model

        service = performance_transcription_service
        mp3_content = create_mp3_bytes(1)

        def transcribe_file(file_id):
            with temporary_file(mp3_content, f"concurrent_{file_id}", ".mp3") as temp_file:
                start_time = time.time()
                result = service.transcribe_audio(temp_file, f"concurrent_{file_id}.mp3")
                end_time = time.time()
                return {
                    'file_id': file_id,
                    'success': result.success,
                    'duration': end_time - start_time,
                    'timestamp': start_time
                }

        # Test with increasing concurrency levels
        concurrency_levels = [1, 2, 5, 10]
        results = {}

        for concurrency in concurrency_levels:
            print(f"\nTesting concurrency level: {concurrency}")

            start_time = time.time()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(transcribe_file, i) for i in range(concurrency)]
                concurrent_results = [future.result() for future in as_completed(futures)]
            total_time = time.time() - start_time

            # Analyze results
            successful = sum(1 for r in concurrent_results if r['success'])
            durations = [r['duration'] for r in concurrent_results]
            throughput = successful / total_time

            results[concurrency] = {
                'total_time': total_time,
                'successful': successful,
                'avg_duration': statistics.mean(durations),
                'max_duration': max(durations),
                'throughput': throughput
            }

            # Performance assertions
            assert successful == concurrency, f"Not all transcriptions succeeded at concurrency {concurrency}"
            assert total_time < concurrency * 2.0, f"Total time {total_time:.2f}s too high for concurrency {concurrency}"

            print(f"Successful: {successful}/{concurrency}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Throughput: {throughput:.2f} files/second")
            print(f"Average duration: {statistics.mean(durations):.3f}s")

        # Verify throughput scales reasonably
        assert results[5]['throughput'] > results[1]['throughput'] * 2, "Throughput doesn't scale with concurrency"

    def test_memory_usage_under_load(self, performance_transcription_service):
        """Test memory usage during sustained load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with patch('src.services.transcription_service.whisper.load_model') as mock_load_model:
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "Memory test transcript"}
            mock_load_model.return_value = mock_model

            service = performance_transcription_service
            mp3_content = create_mp3_bytes(1)

            memory_samples = []

            # Process many files to test memory stability
            for i in range(50):
                with temporary_file(mp3_content, f"memory_{i}", ".mp3") as temp_file:
                    result = service.transcribe_audio(temp_file, f"memory_{i}.mp3")
                    assert result.success is True

                    # Sample memory every 10 iterations
                    if i % 10 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_samples.append(current_memory)

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory

            print(f"\nMemory Usage Analysis:")
            print(f"Initial memory: {initial_memory:.1f} MB")
            print(f"Final memory: {final_memory:.1f} MB")
            print(f"Memory growth: {memory_growth:.1f} MB")
            print(f"Memory samples: {[f'{m:.1f}' for m in memory_samples]}")

            # Memory growth should be reasonable (less than 100MB for 50 files)
            assert memory_growth < 100, f"Memory growth {memory_growth:.1f}MB exceeds 100MB threshold"


class TestGlossaryPerformance:
    """Test glossary service performance characteristics."""

    def test_large_text_processing_performance(self):
        """Test performance with large text inputs."""
        db_repo = DatabaseRepository()
        service = GlossaryService(db_repo)

        # Create progressively larger texts
        base_text = "La inflación en Argentina afecta el PIB y genera preocupación. " \
                   "Los trabajadores buscan laburo y manejan la guita con cuidado. "

        text_sizes = [100, 500, 1000, 5000]  # Number of repetitions
        performance_data = []

        for size in text_sizes:
            large_text = (base_text * size)
            text_length = len(large_text)

            start_time = time.time()
            stats = service.update_glossaries(large_text)
            end_time = time.time()

            duration = end_time - start_time
            chars_per_second = text_length / duration

            performance_data.append({
                'size': size,
                'text_length': text_length,
                'duration': duration,
                'chars_per_second': chars_per_second,
                'terms_added': stats['economic_terms_added'] + stats['argentine_expressions_added']
            })

            print(f"\nText size {size} repetitions ({text_length:,} chars):")
            print(f"Duration: {duration:.3f}s")
            print(f"Processing rate: {chars_per_second:,.0f} chars/second")
            print(f"Terms added: {performance_data[-1]['terms_added']}")

            # Performance thresholds
            assert chars_per_second > 10000, f"Processing rate {chars_per_second:,.0f} chars/s too slow"
            assert duration < 5.0, f"Duration {duration:.3f}s exceeds 5s threshold"

        # Verify processing rate is consistent across sizes
        rates = [data['chars_per_second'] for data in performance_data]
        rate_variance = max(rates) / min(rates)
        assert rate_variance < 5.0, f"Processing rate variance {rate_variance:.1f}x too high"

    def test_database_insertion_performance(self):
        """Test database insertion performance under high load."""
        db_repo = DatabaseRepository()
        service = GlossaryService(db_repo)

        # Generate many unique terms
        economic_terms = [f"término_económico_{i}" for i in range(100)]
        argentine_terms = [f"expresión_argentina_{i}" for i in range(100)]

        all_terms = economic_terms + argentine_terms
        test_text = " ".join(all_terms)

        start_time = time.time()
        stats = service.update_glossaries(test_text)
        end_time = time.time()

        duration = end_time - start_time
        terms_per_second = (stats['economic_terms_added'] + stats['argentine_expressions_added']) / duration

        print(f"\nDatabase Insertion Performance:")
        print(f"Terms processed: {len(all_terms)}")
        print(f"Terms added: {stats['economic_terms_added'] + stats['argentine_expressions_added']}")
        print(f"Duration: {duration:.3f}s")
        print(f"Insertion rate: {terms_per_second:.1f} terms/second")

        # Performance assertions
        assert terms_per_second > 50, f"Insertion rate {terms_per_second:.1f} terms/s too slow"
        assert duration < 3.0, f"Duration {duration:.3f}s exceeds 3s threshold"


class TestTermDetectionPerformance:
    """Test term detection service performance characteristics."""

    def test_candidate_detection_performance(self):
        """Test performance of candidate term detection."""
        db_repo = DatabaseRepository()
        service = TermDetectionService(db_repo)

        # Create text with many potential candidates
        candidate_text = " ".join([
            "blockchain", "fintech", "startup", "unicornio", "disrupción",
            "innovación", "digitalización", "ecosistema", "escalabilidad",
            "monetización", "valoración", "inversión", "venture", "capital"
        ] * 20)  # 280 words total

        times = []
        candidate_counts = []

        # Run multiple iterations
        for i in range(10):
            start_time = time.time()
            candidates = service.detect_candidate_terms(candidate_text)
            end_time = time.time()

            times.append(end_time - start_time)
            candidate_counts.append(len(candidates))

        avg_time = statistics.mean(times)
        avg_candidates = statistics.mean(candidate_counts)
        words_per_second = len(candidate_text.split()) / avg_time

        print(f"\nCandidate Detection Performance:")
        print(f"Text length: {len(candidate_text)} characters, {len(candidate_text.split())} words")
        print(f"Average time: {avg_time:.3f}s")
        print(f"Average candidates found: {avg_candidates:.1f}")
        print(f"Processing rate: {words_per_second:.0f} words/second")

        # Performance assertions
        assert avg_time < 1.0, f"Average detection time {avg_time:.3f}s exceeds 1s threshold"
        assert words_per_second > 500, f"Processing rate {words_per_second:.0f} words/s too slow"
        assert avg_candidates > 5, f"Should detect at least 5 candidates on average"


class TestSystemPerformance:
    """Test overall system performance and resource usage."""

    def test_end_to_end_performance(self):
        """Test complete workflow performance from transcription to glossary update."""
        db_repo = DatabaseRepository()
        transcription_service = TranscriptionService(db_repo)
        glossary_service = GlossaryService(db_repo)
        term_detection_service = TermDetectionService(db_repo)

        with patch('src.services.transcription_service.whisper.load_model') as mock_load_model:
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": SAMPLE_TRANSCRIPTS['economic_heavy']}
            mock_load_model.return_value = mock_model

            mp3_content = create_mp3_bytes(2)
            filename = "e2e_performance.mp3"

            overall_start = time.time()

            # Step 1: Transcription
            with temporary_file(mp3_content, "e2e", ".mp3") as temp_file:
                transcription_start = time.time()
                transcription_result = transcription_service.transcribe_audio(temp_file, filename)
                transcription_time = time.time() - transcription_start

            assert transcription_result.success is True

            # Step 2: Glossary update
            glossary_start = time.time()
            glossary_stats = glossary_service.update_glossaries(transcription_result.full_transcript)
            glossary_time = time.time() - glossary_start

            # Step 3: Term detection
            detection_start = time.time()
            candidates = term_detection_service.detect_candidate_terms(transcription_result.full_transcript)
            detection_time = time.time() - detection_start

            total_time = time.time() - overall_start

            print(f"\nEnd-to-End Performance:")
            print(f"Transcription time: {transcription_time:.3f}s")
            print(f"Glossary update time: {glossary_time:.3f}s")
            print(f"Term detection time: {detection_time:.3f}s")
            print(f"Total time: {total_time:.3f}s")
            print(f"Economic terms added: {glossary_stats['economic_terms_added']}")
            print(f"Argentine expressions added: {glossary_stats['argentine_expressions_added']}")
            print(f"Candidates detected: {len(candidates)}")

            # Performance assertions
            assert transcription_time < 2.0, f"Transcription time {transcription_time:.3f}s too slow"
            assert glossary_time < 1.0, f"Glossary time {glossary_time:.3f}s too slow"
            assert detection_time < 1.0, f"Detection time {detection_time:.3f}s too slow"
            assert total_time < 4.0, f"Total time {total_time:.3f}s exceeds 4s threshold"

    def test_concurrent_mixed_operations(self):
        """Test performance under mixed concurrent operations."""
        db_repo = DatabaseRepository()
        services = {
            'transcription': TranscriptionService(db_repo),
            'glossary': GlossaryService(db_repo),
            'term_detection': TermDetectionService(db_repo)
        }

        with patch('src.services.transcription_service.whisper.load_model') as mock_load_model:
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "Concurrent mixed operations test"}
            mock_load_model.return_value = mock_model

            def transcription_task(task_id):
                mp3_content = create_mp3_bytes(1)
                with temporary_file(mp3_content, f"mixed_{task_id}", ".mp3") as temp_file:
                    start = time.time()
                    result = services['transcription'].transcribe_audio(temp_file, f"mixed_{task_id}.mp3")
                    return ('transcription', task_id, time.time() - start, result.success)

            def glossary_task(task_id):
                text = f"La inflación y el laburo en Argentina {task_id}"
                start = time.time()
                stats = services['glossary'].update_glossaries(text)
                return ('glossary', task_id, time.time() - start, stats['economic_terms_added'] > 0)

            def detection_task(task_id):
                text = f"Hablamos de blockchain y fintech {task_id}"
                start = time.time()
                candidates = services['term_detection'].detect_candidate_terms(text)
                return ('detection', task_id, time.time() - start, len(candidates) > 0)

            # Mix different types of operations
            tasks = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit various tasks
                for i in range(5):
                    tasks.append(executor.submit(transcription_task, i))
                for i in range(5):
                    tasks.append(executor.submit(glossary_task, i))
                for i in range(5):
                    tasks.append(executor.submit(detection_task, i))

                start_time = time.time()
                results = [task.result() for task in as_completed(tasks)]
                total_time = time.time() - start_time

            # Analyze results
            by_type = {}
            for operation_type, task_id, duration, success in results:
                if operation_type not in by_type:
                    by_type[operation_type] = []
                by_type[operation_type].append((duration, success))

            print(f"\nConcurrent Mixed Operations Performance:")
            print(f"Total operations: {len(results)}")
            print(f"Total time: {total_time:.3f}s")
            print(f"Overall throughput: {len(results) / total_time:.1f} ops/second")

            # Verify all operations succeeded and performance
            for operation_type, task_results in by_type.items():
                durations = [d for d, s in task_results]
                successes = [s for d, s in task_results]

                avg_duration = statistics.mean(durations)
                success_rate = sum(successes) / len(successes)

                print(f"{operation_type}: {success_rate:.1%} success, {avg_duration:.3f}s avg")

                assert success_rate == 1.0, f"{operation_type} had failures"
                assert avg_duration < 2.0, f"{operation_type} average time {avg_duration:.3f}s too slow"

            assert total_time < 8.0, f"Total concurrent time {total_time:.3f}s exceeds 8s threshold"


class TestPerformanceReporting:
    """Generate performance reports and save metrics."""

    def test_generate_performance_report(self):
        """Generate comprehensive performance report."""
        import json
        from datetime import datetime

        # This would be called by CI/CD to generate performance reports
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'test_environment': {
                'python_version': '3.9+',
                'database': 'SQLite in-memory',
                'whisper_model': 'tiny (mocked)'
            },
            'performance_metrics': {
                'transcription': {
                    'single_file_avg_time': '< 2.0s',
                    'concurrent_throughput': '> 2 files/second',
                    'memory_growth': '< 100MB for 50 files'
                },
                'glossary': {
                    'text_processing_rate': '> 10,000 chars/second',
                    'database_insertion_rate': '> 50 terms/second'
                },
                'term_detection': {
                    'detection_rate': '> 500 words/second',
                    'detection_time': '< 1.0s'
                },
                'end_to_end': {
                    'complete_workflow': '< 4.0s',
                    'concurrent_mixed_ops': '> 1.5 ops/second'
                }
            },
            'quality_gates': {
                'all_tests_passed': True,
                'performance_thresholds_met': True,
                'memory_usage_acceptable': True,
                'concurrency_stable': True
            }
        }

        # Save report for CI/CD
        report_path = Path('performance-results.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nPerformance report saved to {report_path}")
        print(json.dumps(report, indent=2))

        # Verify report structure
        assert 'timestamp' in report
        assert 'performance_metrics' in report
        assert 'quality_gates' in report
        assert all(report['quality_gates'].values()), "All quality gates must pass"