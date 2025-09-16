"""
Comprehensive API endpoint tests covering all FastAPI endpoints,
request/response validation, error handling, and integration scenarios.
"""
import pytest
from unittest.mock import patch, Mock
import json

from tests.fixtures.test_data import create_mp3_bytes, create_malicious_file_bytes, create_oversized_file_bytes
from tests.utils.test_helpers import assert_response_structure


class TestHealthEndpoint:
    """Test health check endpoint functionality."""

    @pytest.mark.asyncio
    async def test_health_endpoint_success(self, async_client):
        """Test health endpoint returns successful response."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert_response_structure(data, ["status", "version"])
        assert data["status"] == "healthy"
        assert data["version"] == "1.0"

    def test_health_endpoint_sync_client(self, test_client):
        """Test health endpoint with synchronous client."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_response_headers(self, async_client):
        """Test health endpoint response headers."""
        response = await async_client.get("/health")

        assert response.headers["content-type"] == "application/json"


class TestUploadEndpoint:
    """Test file upload endpoint functionality."""

    @pytest.mark.asyncio
    async def test_upload_valid_mp3_file(self, async_client, temp_upload_dir):
        """Test uploading valid MP3 file."""
        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "Test transcription with inflación and laburo"
            }
            mock_whisper.return_value = mock_model

            files = {"file": ("test_audio.mp3", mp3_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 200
            data = response.json()

            expected_keys = ["filename", "transcript_preview", "message", "stats"]
            assert_response_structure(data, expected_keys)

            assert data["filename"] == "test_audio.mp3"
            assert data["transcript_preview"]
            assert "processed" in data["message"].lower()
            assert isinstance(data["stats"], dict)

    @pytest.mark.asyncio
    async def test_upload_file_without_filename(self, async_client, temp_upload_dir):
        """Test upload with no filename provided."""
        mp3_content = create_mp3_bytes(1)

        files = {"file": ("", mp3_content, "audio/mpeg")}
        response = await async_client.post("/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "filename" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_non_mp3_file(self, async_client, temp_upload_dir):
        """Test upload with non-MP3 file."""
        content = b"This is not an MP3 file"

        files = {"file": ("document.txt", content, "text/plain")}
        response = await async_client.post("/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "mp3" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, async_client, temp_upload_dir):
        """Test upload with file exceeding size limits."""
        oversized_content = create_oversized_file_bytes(10)  # 10MB > 5MB limit

        files = {"file": ("large_file.mp3", oversized_content, "audio/mpeg")}
        response = await async_client.post("/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "validation" in data["detail"].lower() or "size" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_malicious_file(self, async_client, temp_upload_dir):
        """Test upload with malicious file content."""
        malicious_content = create_malicious_file_bytes()

        with patch('src.services.transcription_service.magic.from_file') as mock_magic:
            mock_magic.return_value = 'application/x-executable'

            files = {"file": ("malicious.mp3", malicious_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_transcription_failure(self, async_client, temp_upload_dir):
        """Test upload when transcription fails."""
        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.side_effect = Exception("Transcription failed")
            mock_whisper.return_value = mock_model

            files = {"file": ("test_audio.mp3", mp3_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 500
            data = response.json()
            assert "transcription" in data["detail"].lower() or "failed" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_file_save_failure(self, async_client, temp_upload_dir):
        """Test upload when file save fails."""
        mp3_content = create_mp3_bytes(1)

        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            files = {"file": ("test_audio.mp3", mp3_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 500
            data = response.json()
            assert "failed to save" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_statistics_included(self, async_client, temp_upload_dir):
        """Test that upload response includes processing statistics."""
        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "Test transcription with inflación, PIB and laburo, guita"
            }
            mock_whisper.return_value = mock_model

            files = {"file": ("test_audio.mp3", mp3_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 200
            data = response.json()

            # Check that stats are included
            assert "stats" in data
            stats = data["stats"]

            expected_stat_keys = ["economic_terms_added", "argentine_expressions_added", "new_candidates_added"]
            for key in expected_stat_keys:
                assert key in stats
                assert isinstance(stats[key], int)

    @pytest.mark.asyncio
    async def test_upload_unicode_filename(self, async_client, temp_upload_dir):
        """Test upload with unicode characters in filename."""
        mp3_content = create_mp3_bytes(1)
        unicode_filename = "audio_niños_corazón.mp3"

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "Test transcription"}
            mock_whisper.return_value = mock_model

            files = {"file": (unicode_filename, mp3_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == unicode_filename

    @pytest.mark.asyncio
    async def test_upload_no_file_provided(self, async_client, temp_upload_dir):
        """Test upload endpoint with no file provided."""
        response = await async_client.post("/upload")

        assert response.status_code == 422  # Validation error


class TestGlossariesEndpoint:
    """Test glossaries retrieval endpoint functionality."""

    @pytest.mark.asyncio
    async def test_get_glossaries_empty_database(self, async_client):
        """Test getting glossaries from empty database."""
        response = await async_client.get("/glossaries")

        assert response.status_code == 200
        data = response.json()

        expected_keys = ["economic_glossary", "argentine_dictionary"]
        assert_response_structure(data, expected_keys)

        assert isinstance(data["economic_glossary"], list)
        assert isinstance(data["argentine_dictionary"], list)

    @pytest.mark.asyncio
    async def test_get_glossaries_with_data(self, async_client, populated_db_repository):
        """Test getting glossaries with existing data."""
        # The populated_db_repository fixture should have data
        response = await async_client.get("/glossaries")

        assert response.status_code == 200
        data = response.json()

        assert len(data["economic_glossary"]) > 0
        assert len(data["argentine_dictionary"]) > 0

        # Check structure of returned data
        for term_data in data["economic_glossary"]:
            assert isinstance(term_data, list)
            assert len(term_data) == 3  # term, category, first_seen

        for expr_data in data["argentine_dictionary"]:
            assert isinstance(expr_data, list)
            assert len(expr_data) == 2  # expression, first_seen

    @pytest.mark.asyncio
    async def test_get_glossaries_database_error(self, async_client):
        """Test glossaries endpoint when database error occurs."""
        with patch('src.services.glossary_service.GlossaryService.get_glossaries') as mock_get:
            mock_get.side_effect = Exception("Database error")

            response = await async_client.get("/glossaries")

            assert response.status_code == 500
            data = response.json()
            assert "failed to retrieve" in data["detail"].lower()


class TestCandidatesEndpoint:
    """Test candidates retrieval endpoint functionality."""

    @pytest.mark.asyncio
    async def test_get_candidates_empty_database(self, async_client):
        """Test getting candidates from empty database."""
        response = await async_client.get("/candidates")

        assert response.status_code == 200
        data = response.json()

        expected_keys = ["candidates", "stats"]
        assert_response_structure(data, expected_keys)

        assert isinstance(data["candidates"], list)
        assert isinstance(data["stats"], dict)
        assert len(data["candidates"]) == 0

    @pytest.mark.asyncio
    async def test_get_candidates_with_data(self, async_client, populated_db_repository):
        """Test getting candidates with existing data."""
        response = await async_client.get("/candidates")

        assert response.status_code == 200
        data = response.json()

        # Should have candidates from populated database
        assert len(data["candidates"]) > 0

        # Check structure
        for candidate_data in data["candidates"]:
            assert isinstance(candidate_data, list)
            assert len(candidate_data) == 3  # term, first_seen, context

        # Check stats structure
        stats = data["stats"]
        assert "total_candidates" in stats
        assert "unique_candidates" in stats

    @pytest.mark.asyncio
    async def test_get_candidates_database_error(self, async_client):
        """Test candidates endpoint when database error occurs."""
        with patch('src.services.term_detection_service.TermDetectionService.get_candidates') as mock_get:
            mock_get.side_effect = Exception("Database error")

            response = await async_client.get("/candidates")

            assert response.status_code == 500


class TestPromoteEndpoint:
    """Test candidate promotion endpoint functionality."""

    @pytest.mark.asyncio
    async def test_promote_candidate_to_economic_success(self, async_client, populated_db_repository):
        """Test successful promotion of candidate to economic glossary."""
        term = "blockchain"

        response = await async_client.post(
            f"/promote?term={term}&glossary=economic"
        )

        assert response.status_code == 200
        data = response.json()
        assert "promoted" in data["message"].lower()
        assert term in data["message"]
        assert "economic" in data["message"]

    @pytest.mark.asyncio
    async def test_promote_candidate_to_argentine_success(self, async_client, populated_db_repository):
        """Test successful promotion of candidate to Argentine dictionary."""
        term = "fintech"

        response = await async_client.post(
            f"/promote?term={term}&glossary=argentine"
        )

        assert response.status_code == 200
        data = response.json()
        assert "promoted" in data["message"].lower()
        assert term in data["message"]
        assert "argentine" in data["message"]

    @pytest.mark.asyncio
    async def test_promote_nonexistent_candidate(self, async_client):
        """Test promotion of non-existent candidate."""
        response = await async_client.post(
            "/promote?term=nonexistent&glossary=economic"
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_promote_invalid_glossary(self, async_client, populated_db_repository):
        """Test promotion with invalid glossary parameter."""
        response = await async_client.post(
            "/promote?term=blockchain&glossary=invalid"
        )

        assert response.status_code == 400
        data = response.json()
        assert "economic" in data["detail"] and "argentine" in data["detail"]

    @pytest.mark.asyncio
    async def test_promote_candidate_already_exists(self, async_client):
        """Test promotion when term already exists in target glossary."""
        # This test would need setup where a term exists in both candidates and target glossary
        # Implementation depends on how the service handles this case

        term = "existing_term"

        # First add to economic glossary and candidates
        # Then try to promote - should fail

        response = await async_client.post(
            f"/promote?term={term}&glossary=economic"
        )

        # Depending on implementation, might be 409 (conflict) or 404 (not found)
        assert response.status_code in [404, 409]

    @pytest.mark.asyncio
    async def test_promote_missing_parameters(self, async_client):
        """Test promotion endpoint with missing parameters."""
        # Missing term parameter
        response1 = await async_client.post("/promote?glossary=economic")
        assert response1.status_code == 422

        # Missing glossary parameter
        response2 = await async_client.post("/promote?term=blockchain")
        assert response2.status_code == 422

        # Missing both parameters
        response3 = await async_client.post("/promote")
        assert response3.status_code == 422

    @pytest.mark.asyncio
    async def test_promote_unicode_term(self, async_client):
        """Test promotion with unicode characters in term."""
        # Add unicode candidate first (would need setup)
        term = "niños"

        response = await async_client.post(
            f"/promote?term={term}&glossary=economic"
        )

        # Depending on whether candidate exists, could be 200 or 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_promote_database_error(self, async_client, populated_db_repository):
        """Test promotion when database error occurs."""
        with patch('src.services.glossary_service.GlossaryService.promote_candidate_to_economic') as mock_promote:
            mock_promote.side_effect = Exception("Database error")

            response = await async_client.post(
                "/promote?term=blockchain&glossary=economic"
            )

            assert response.status_code == 500


class TestDeleteCandidateEndpoint:
    """Test candidate deletion endpoint functionality."""

    @pytest.mark.asyncio
    async def test_delete_candidate_success(self, async_client, populated_db_repository):
        """Test successful deletion of candidate term."""
        term = "blockchain"  # Should exist in populated database

        response = await async_client.delete(f"/candidates/{term}")

        assert response.status_code == 200
        data = response.json()
        assert "removed successfully" in data["message"]
        assert term in data["message"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_candidate(self, async_client):
        """Test deletion of non-existent candidate."""
        response = await async_client.delete("/candidates/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_candidate_with_special_characters(self, async_client):
        """Test deletion of candidate with special characters."""
        term = "web3.0"  # URL encoding test

        response = await async_client.delete(f"/candidates/{term}")

        # Should handle URL encoding properly
        assert response.status_code in [200, 404]  # Depending on existence

    @pytest.mark.asyncio
    async def test_delete_candidate_unicode(self, async_client):
        """Test deletion of candidate with unicode characters."""
        term = "niños"

        response = await async_client.delete(f"/candidates/{term}")

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_delete_candidate_database_error(self, async_client):
        """Test deletion when database error occurs."""
        with patch('src.services.term_detection_service.TermDetectionService.remove_candidate') as mock_remove:
            mock_remove.side_effect = Exception("Database error")

            response = await async_client.delete("/candidates/test")

            assert response.status_code == 500


class TestEndpointIntegration:
    """Test integration scenarios across multiple endpoints."""

    @pytest.mark.asyncio
    async def test_full_workflow_upload_to_promotion(self, async_client, temp_upload_dir):
        """Test complete workflow from upload to candidate promotion."""
        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "blockchain technology is revolutionizing fintech industry"
            }
            mock_whisper.return_value = mock_model

            # Step 1: Upload file
            files = {"file": ("test_audio.mp3", mp3_content, "audio/mpeg")}
            upload_response = await async_client.post("/upload", files=files)

            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            assert upload_data["stats"]["new_candidates_added"] > 0

            # Step 2: Get candidates
            candidates_response = await async_client.get("/candidates")
            assert candidates_response.status_code == 200
            candidates_data = candidates_response.json()
            assert len(candidates_data["candidates"]) > 0

            # Step 3: Promote a candidate
            candidate_term = candidates_data["candidates"][0][0]
            promote_response = await async_client.post(
                f"/promote?term={candidate_term}&glossary=economic"
            )

            assert promote_response.status_code == 200

            # Step 4: Verify promotion in glossaries
            glossaries_response = await async_client.get("/glossaries")
            assert glossaries_response.status_code == 200
            glossaries_data = glossaries_response.json()

            # Should find the promoted term in economic glossary
            economic_terms = [term[0] for term in glossaries_data["economic_glossary"]]
            assert candidate_term in economic_terms

    @pytest.mark.asyncio
    async def test_multiple_uploads_accumulate_data(self, async_client, temp_upload_dir):
        """Test that multiple uploads accumulate data correctly."""
        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_whisper.return_value = mock_model

            # Upload 1: Economic terms
            mock_model.transcribe.return_value = {"text": "inflación PIB reservas"}
            files1 = {"file": ("economic.mp3", mp3_content, "audio/mpeg")}
            response1 = await async_client.post("/upload", files=files1)
            assert response1.status_code == 200

            # Upload 2: Argentine expressions
            mock_model.transcribe.return_value = {"text": "laburo guita quilombo"}
            files2 = {"file": ("argentine.mp3", mp3_content, "audio/mpeg")}
            response2 = await async_client.post("/upload", files=files2)
            assert response2.status_code == 200

            # Check accumulated data
            glossaries_response = await async_client.get("/glossaries")
            assert glossaries_response.status_code == 200
            glossaries_data = glossaries_response.json()

            assert len(glossaries_data["economic_glossary"]) >= 3
            assert len(glossaries_data["argentine_dictionary"]) >= 3

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self, async_client):
        """Test that all endpoints handle errors consistently."""
        # Test various error scenarios and ensure consistent response format

        error_responses = []

        # 1. Upload with invalid file
        files = {"file": ("test.txt", b"not audio", "text/plain")}
        upload_response = await async_client.post("/upload", files=files)
        error_responses.append(upload_response)

        # 2. Promote non-existent candidate
        promote_response = await async_client.post("/promote?term=fake&glossary=economic")
        error_responses.append(promote_response)

        # 3. Delete non-existent candidate
        delete_response = await async_client.delete("/candidates/fake")
        error_responses.append(delete_response)

        # All error responses should have consistent structure
        for response in error_responses:
            assert response.status_code >= 400
            data = response.json()
            assert "detail" in data  # FastAPI standard error format

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, async_client, temp_upload_dir):
        """Test API behavior under concurrent requests."""
        import asyncio

        mp3_content = create_mp3_bytes(1)

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "concurrent test transcript"}
            mock_whisper.return_value = mock_model

            # Create multiple concurrent requests
            async def upload_file(file_num):
                files = {"file": (f"concurrent_{file_num}.mp3", mp3_content, "audio/mpeg")}
                response = await async_client.post("/upload", files=files)
                return response

            # Execute concurrent uploads
            tasks = [upload_file(i) for i in range(5)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_content_type_validation(self, async_client):
        """Test API content type handling."""
        # Test various content types to ensure proper handling

        # Valid JSON endpoints should work
        glossaries_response = await async_client.get("/glossaries")
        assert glossaries_response.headers["content-type"] == "application/json"

        candidates_response = await async_client.get("/candidates")
        assert candidates_response.headers["content-type"] == "application/json"

        health_response = await async_client.get("/health")
        assert health_response.headers["content-type"] == "application/json"