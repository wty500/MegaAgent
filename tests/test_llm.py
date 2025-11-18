"""
Tests for LLM module functionality including web search capabilities.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Import the modules to test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import llm
import config


class TestWebSearchTool:
    """Test the web_search tool functionality."""

    def test_web_search_tool_in_tools_when_enabled(self, mock_config):
        """Test that web_search tool is included in tools list when enabled."""
        with patch('llm.config', mock_config):
            llm.gen_tools('test_agent')
            # Check if web_search tool is in the tools list
            tool_names = [tool['name'] for tool in llm.tools]
            assert 'web_search' in tool_names

    def test_web_search_tool_not_in_tools_when_disabled(self, mock_config):
        """Test that web_search tool is not included when disabled."""
        mock_config.enable_web_search = False
        with patch('llm.config', mock_config):
            llm.gen_tools('test_agent')
            tool_names = [tool['name'] for tool in llm.tools]
            assert 'web_search' not in tool_names

    def test_web_search_function_disabled(self, mock_config):
        """Test that web_search function returns error when disabled."""
        mock_config.enable_web_search = False
        with patch('llm.config', mock_config):
            result = llm.web_search('test query')
            assert 'error' in result
            assert 'not enabled' in result['error']

    def test_web_search_function_success(self, mock_config, mock_requests_post, mock_web_search_response):
        """Test successful web search execution."""
        mock_config.enable_web_search = True
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'choices': [
                        {
                            'message': {
                                'content': 'Search results here'
                            }
                        }
                    ]
                }
                mock_post.return_value = mock_response

                result = llm.web_search('test query', max_results=5)
                assert result['status'] == 'success'
                assert result['query'] == 'test query'
                assert result['max_results'] == 5

    def test_web_search_function_timeout(self, mock_config):
        """Test web search timeout handling."""
        mock_config.enable_web_search = True
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                import requests
                mock_post.side_effect = requests.exceptions.Timeout()
                result = llm.web_search('test query')
                assert 'error' in result
                assert 'timed out' in result['error']

    def test_web_search_function_api_error(self, mock_config):
        """Test web search API error handling."""
        mock_config.enable_web_search = True
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = 'Internal Server Error'
                mock_post.return_value = mock_response
                result = llm.web_search('test query')
                assert 'error' in result
                assert '500' in result['error']


class TestGenTools:
    """Test the gen_tools function."""

    def test_gen_tools_includes_basic_tools(self, mock_config):
        """Test that gen_tools includes all basic tools."""
        with patch('llm.config', mock_config):
            llm.gen_tools('test_agent')
            tool_names = [tool['name'] for tool in llm.tools]
            # Check for essential tools
            assert 'exec_python_file' in tool_names
            assert 'read_file' in tool_names
            assert 'write_file' in tool_names
            assert 'add_agent' in tool_names
            assert 'talk' in tool_names
            assert 'terminate' in tool_names

    def test_gen_tools_with_shared_files(self, mock_config):
        """Test gen_tools correctly handles file sharing."""
        llm.written_files = {
            'agent1': ['test1.py', 'test2.txt', 'status_agent1.txt', 'todo_agent1.txt'],
            'agent2': ['test3.py']
        }
        with patch('llm.config', mock_config):
            llm.gen_tools('agent1')
            # Find the read_file tool
            read_file_tool = next((t for t in llm.tools if t['name'] == 'read_file'), None)
            assert read_file_tool is not None
            # Should include files but not status/todo files
            assert 'test1.py' in read_file_tool['description']
            assert 'test2.txt' in read_file_tool['description']
            assert 'status_agent1.txt' not in read_file_tool['description']


class TestTokenCounting:
    """Test token counting in LLM responses."""

    def test_token_counting_in_response(self, mock_config, mock_openai_response):
        """Test that token counts are properly tracked."""
        initial_input = llm.input_token
        initial_output = llm.output_token
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = mock_openai_response
                mock_post.return_value = mock_response
                result = llm.get_llm_response([{'role': 'user', 'content': 'test'}])
                # Verify tokens were counted
                assert llm.input_token >= initial_input + 100
                assert llm.output_token >= initial_output + 50


class TestLLMResponseHandling:
    """Test LLM response handling and error cases."""

    def test_get_llm_response_retry_on_error(self, mock_config):
        """Test that get_llm_response retries on API errors."""
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                # First call fails, second succeeds
                error_response = {'error': 'API Error'}
                success_response = {
                    'choices': [{'message': {'content': 'test'}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 5}
                }
                mock_post.side_effect = [error_response, success_response]

                with patch('llm._get_llm_response') as mock_get:
                    mock_get.side_effect = [error_response, success_response]
                    result = llm.get_llm_response([{'role': 'user', 'content': 'test'}])
                    # Should attempt to get response
                    assert mock_get.called

    def test_get_llm_response_with_tools(self, mock_config, mock_openai_response):
        """Test get_llm_response with tools enabled."""
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = mock_openai_response
                mock_post.return_value = mock_response

                result = llm.get_llm_response(
                    [{'role': 'user', 'content': 'test'}],
                    enable_tools=True
                )
                assert 'choices' in result

    def test_get_llm_response_without_tools(self, mock_config, mock_openai_response):
        """Test get_llm_response with tools disabled."""
        with patch('llm.config', mock_config):
            with patch('llm.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = mock_openai_response
                mock_post.return_value = mock_response

                result = llm.get_llm_response(
                    [{'role': 'user', 'content': 'test'}],
                    enable_tools=False
                )
                assert 'choices' in result
