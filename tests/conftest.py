"""
Pytest configuration and shared fixtures for MegaAgent tests.
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_config():
    """Create a mock config module with test values."""
    config = Mock()
    config.api_key = 'test-api-key'
    config.model = 'gpt-5.1'
    config.url = 'https://api.openai.com/v1/chat/completions'
    config.MAX_MEMORY = 10
    config.MAX_ROUNDS = 20
    config.MAX_SUBORDINATES = 5
    config.share_file = True
    config.ceo_name = 'Bob'
    config.enable_web_search = True
    config.web_search_provider = 'openai'
    return config


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    return {
        'id': 'chatcmpl-test',
        'object': 'chat.completion',
        'created': 1234567890,
        'model': 'gpt-5.1',
        'choices': [
            {
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': '[{"function_name": "terminate", "arguments": {}}]'
                },
                'finish_reason': 'function_call'
            }
        ],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }


@pytest.fixture
def temp_files_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp(prefix='megaagent_test_')
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_requests_post(mock_openai_response):
    """Create a mock for requests.post."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openai_response
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_web_search_response():
    """Create a mock web search response."""
    return {
        'status': 'success',
        'query': 'test search query',
        'results': [
            {
                'title': 'Test Result 1',
                'url': 'https://example.com/1',
                'snippet': 'This is a test search result'
            },
            {
                'title': 'Test Result 2',
                'url': 'https://example.com/2',
                'snippet': 'Another test search result'
            }
        ],
        'max_results': 5
    }
