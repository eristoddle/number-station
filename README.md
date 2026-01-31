# Number Station 📡

A comprehensive dashboard tool for content aggregation and curation. Number Station provides a unified interface for monitoring multiple content sources including RSS feeds, social networks, and websites through an extensible plugin architecture.

## Features

- **Dual UI Modes**: Stream mode (chronological feed) and Board mode (multi-column layout)
- **Content Aggregation**: RSS feeds, social media, and custom web scraping
- **Plugin Architecture**: Extensible system for adding new content sources and features
- **Themable Interface**: Customizable visual themes
- **Docker Support**: Containerized deployment for consistent environments

## Quick Start

### Using Docker (Recommended)

1. **Clone and start the application:**
   ```bash
   git clone <repository-url>
   cd number-station
   docker-compose up --build
   ```

2. **Access the dashboard:**
   Open your browser to [http://localhost:8501](http://localhost:8501)

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   streamlit run src/main.py
   ```

## Project Structure

```
number-station/
├── src/                    # Main source code
│   ├── __init__.py
│   └── main.py            # Application entry point
├── plugins/               # Plugin modules
│   └── __init__.py
├── config/                # Configuration files
│   └── __init__.py
├── tests/                 # Test suite
│   └── __init__.py
├── data/                  # Data storage (created at runtime)
├── logs/                  # Application logs (created at runtime)
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Multi-container setup
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run property-based tests
pytest tests/ -k "property"
```

### Code Quality

```bash
# Format code
black src/ plugins/ tests/

# Lint code
flake8 src/ plugins/ tests/

# Type checking
mypy src/
```

## Configuration

Configuration files are stored in the `config/` directory and data is persisted in the `data/` directory. Both directories are created automatically when the application starts.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[License information to be added]

## Architecture

Number Station is built on a modular plugin architecture that allows for easy extension and customization. The system supports:

- **Content Sources**: RSS feeds, social media APIs, web scraping
- **Content Filters**: Ranking, categorization, and processing plugins
- **UI Themes**: Customizable visual styling
- **Future AI Features**: Designed to support machine learning enhancements

For detailed architecture information, see the design documentation in `.kiro/specs/number-station/design.md`.