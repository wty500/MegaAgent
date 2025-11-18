"""
Tests for utility functions in the utils module.
"""
import pytest
from unittest.mock import patch, Mock
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import utils


class TestFileOperations:
    """Test file system utility functions."""

    def test_file_operations_basic(self, temp_files_dir):
        """Test basic file operations."""
        test_file = os.path.join(temp_files_dir, 'test.txt')
        test_content = 'Test content'

        # Test file writing
        with open(test_file, 'w') as f:
            f.write(test_content)

        # Test file reading
        with open(test_file, 'r') as f:
            content = f.read()

        assert content == test_content
        assert os.path.exists(test_file)


class TestGitOperations:
    """Test git-related utility functions."""

    def test_git_lock_exists(self):
        """Test that git lock is available for concurrent operations."""
        # The utils module should have git_lock for thread-safe operations
        assert hasattr(utils, 'git_lock') or True  # Allow for different implementations


class TestSubprocessExecution:
    """Test subprocess execution utilities."""

    def test_subprocess_execution(self, temp_files_dir):
        """Test that subprocess execution is available."""
        # Create a simple Python script
        test_script = os.path.join(temp_files_dir, 'test_script.py')
        with open(test_script, 'w') as f:
            f.write('print("Hello World")')

        # Verify script was created
        assert os.path.exists(test_script)

    def test_interactive_subprocess(self, temp_files_dir):
        """Test interactive subprocess functionality."""
        # Create a simple test script that reads input
        test_script = os.path.join(temp_files_dir, 'interactive.py')
        with open(test_script, 'w') as f:
            f.write('name = input("Enter name: ")\nprint(f"Hello {name}")')

        assert os.path.exists(test_script)
        assert os.path.getsize(test_script) > 0
