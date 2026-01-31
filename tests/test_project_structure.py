"""
Test basic project structure and imports
"""
import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_project_directories_exist():
    """Test that all required project directories exist"""
    required_dirs = ["src", "plugins", "config", "tests"]

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        assert dir_path.exists(), f"Directory {dir_name} should exist"
        assert dir_path.is_dir(), f"{dir_name} should be a directory"


def test_project_files_exist():
    """Test that all required project files exist"""
    required_files = [
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "README.md",
        "setup.py",
        ".gitignore",
        ".dockerignore",
        "Makefile",
        "pytest.ini"
    ]

    for file_name in required_files:
        file_path = project_root / file_name
        assert file_path.exists(), f"File {file_name} should exist"
        assert file_path.is_file(), f"{file_name} should be a file"


def test_src_main_imports():
    """Test that the main application module can be imported"""
    try:
        import src.main
        assert hasattr(src.main, 'main'), "main.py should have a main() function"
    except ImportError as e:
        pytest.fail(f"Could not import src.main: {e}")


def test_package_init_files():
    """Test that all packages have __init__.py files"""
    packages = ["src", "plugins", "config", "tests"]

    for package in packages:
        init_file = project_root / package / "__init__.py"
        assert init_file.exists(), f"{package}/__init__.py should exist"


def test_requirements_file_content():
    """Test that requirements.txt contains expected dependencies"""
    requirements_file = project_root / "requirements.txt"
    content = requirements_file.read_text()

    expected_deps = ["streamlit", "feedparser", "requests", "pydantic"]

    for dep in expected_deps:
        assert dep in content, f"requirements.txt should contain {dep}"


def test_dockerfile_content():
    """Test that Dockerfile has expected configuration"""
    dockerfile = project_root / "Dockerfile"
    content = dockerfile.read_text()

    expected_elements = [
        "FROM python:3.11-slim",
        "WORKDIR /app",
        "COPY requirements.txt",
        "RUN pip install",
        "EXPOSE 8501",
        "streamlit"
    ]

    for element in expected_elements:
        assert element in content, f"Dockerfile should contain '{element}'"


if __name__ == "__main__":
    pytest.main([__file__])