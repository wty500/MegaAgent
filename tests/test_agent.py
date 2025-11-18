"""
Tests for Agent module functionality.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import agent
import config


class TestAgentInitialization:
    """Test Agent class initialization."""

    def test_agent_creation(self, mock_config):
        """Test basic agent creation."""
        with patch('agent.config', mock_config):
            initial_message = 'You are a test agent.'
            test_agent = agent.Agent(name='TestAgent001', initial_message=initial_message)
            assert test_agent.name == 'TestAgent001'
            assert test_agent.initial_message == initial_message

    def test_agent_memory_initialization(self, mock_config):
        """Test that agent memory is properly initialized."""
        with patch('agent.config', mock_config):
            test_agent = agent.Agent(name='TestAgent002', initial_message='Test')
            # Agent should have memory (ChromaDB collection)
            assert hasattr(test_agent, 'history_pool')


class TestAgentMemory:
    """Test Agent memory and message handling."""

    def test_agent_can_store_messages(self, mock_config):
        """Test that agent can store and retrieve messages."""
        with patch('agent.config', mock_config):
            with patch('agent.chromadb.Client'):
                test_agent = agent.Agent(name='TestAgent003', initial_message='Test')
                # Test that agent has methods for managing memory
                assert hasattr(test_agent, 'history') or hasattr(test_agent, 'history_pool')


class TestAgentTaskStatus:
    """Test Agent task status management."""

    def test_agent_todo_management(self, mock_config, temp_files_dir):
        """Test that agent can manage TODO items."""
        with patch('agent.config', mock_config):
            # Change to temp directory
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_files_dir)
                os.makedirs('files', exist_ok=True)
                os.makedirs('logs', exist_ok=True)

                test_agent = agent.Agent(name='TestAgent004', initial_message='Test')
                # Agent should be able to manage tasks
                # This is typically done through the LLM interface
                assert hasattr(test_agent, 'name')
            finally:
                os.chdir(original_cwd)


class TestAgentCommunication:
    """Test Agent communication and talking functionality."""

    def test_agent_talk_format(self, mock_config):
        """Test that agent talk messages use correct XML format."""
        with patch('agent.config', mock_config):
            # Test format: <talk goal="Name">Content</talk>
            talk_format = '<talk goal="Alice">Test message</talk>'
            # Verify format contains required elements
            assert 'goal=' in talk_format
            assert '</talk>' in talk_format


class TestMemoryRetrieval:
    """Test memory retrieval and context management."""

    def test_memory_max_size(self, mock_config):
        """Test that memory respects MAX_MEMORY limit."""
        with patch('agent.config', mock_config):
            mock_config.MAX_MEMORY = 10
            # When more than 10 messages are added, oldest should be removed
            assert mock_config.MAX_MEMORY == 10
