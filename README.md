# Auto-Man

NPU-Accelerated Manual Generator

Auto-Man is a powerful tool that leverages Neural Processing Units (NPUs) and Large Language Models to automatically generate comprehensive manual pages (.man files) for software projects. It can analyze code repositories and create professional documentation with minimal user intervention.

## Features

- **NPU Acceleration**: Leverages ONNX Runtime with QNN (Qualcomm Neural Network) support for optimal performance on compatible hardware
- **Multi-Modal Interface**: Command-line interface with optional PyQt6 GUI
- **Repository Analysis**: Automatically indexes and analyzes code repositories
- **LLM Integration**: Uses state-of-the-art language models for documentation generation
- **MCP Server Support**: Includes Model Context Protocol server for integration with other tools
- **Cross-Platform**: Works on Windows, Linux, and macOS

## Installation

### Prerequisites

- Python 3.12 or higher
- uv package manager

### Quick Start

1. Clone or download the repository:
```bash
git clone <repository-url>
cd golan-auto-man
```

2. Install dependencies using uv:
```bash
uv sync
```

3. (Optional) For NPU acceleration on supported devices:
```bash
uv sync --extra npu
```

## Usage

### Command Line Interface

#### Basic Usage

Generate a manual for a repository:
```bash
python main.py -r https://github.com/user/repo
```

#### Available Options

- `-m, --model_path PATH`: Path to model directory
- `-r, --repo URL`: Repository URL or local path
- `-p, --prompt TEXT`: Run single generation
- `--mcp`: Start MCP server
- `--gui`: Start PyQt6 GUI
- `--reset`: Uninstall custom models and clear cache
- `-v, --verbose`: Enable verbose output

#### Examples

Generate documentation for a local repository:
```bash
python main.py -r /path/to/local/repo
```

Start the graphical interface:
```bash
python main.py --gui
```

Run a single prompt generation:
```bash
python main.py -p "Explain how this function works"
```

Start MCP server for tool integration:
```bash
python main.py --mcp
```

Reset environment (clears cache and custom models):
```bash
python main.py --reset
```

### GUI Mode

Launch the graphical user interface:
```bash
python main.py --gui
```

The GUI provides an intuitive way to:
- Browse and select repositories
- Configure model settings
- Monitor generation progress
- View generated documentation

### MCP Server Mode

Auto-Man includes a Model Context Protocol server for integration with compatible tools:

```bash
python main.py --mcp
```

The MCP server exposes endpoints for:
- Repository analysis and indexing
- Context retrieval
- Documentation generation

## Model Support

Auto-Man supports various ONNX-compatible models. Models should be placed in the `models/` directory with the following structure:

```
models/
├── model_repo/          # Default model repository
│   └── [model-name]/
│       └── model.onnx
└── [custom-models]/     # Custom model directories
    └── model.onnx
```

### Supported Model Formats

- ONNX models with QNN optimization
- Hugging Face model repositories
- Local model files

## Configuration

### Environment Setup

The tool automatically creates necessary directories:
- `models/`: Model storage
- `.cache/`: Temporary cache files

### Model Configuration

Models are automatically detected from the `models/` directory. You can specify a custom model path using the `--model_path` option.

## Architecture

Auto-Man consists of several key components:

- **Main Entry Point** (`main.py`): Command-line interface and orchestration
- **LLM Engine** (`llm_engine.py`): Language model inference
- **RAG System** (`rag.py`): Retrieval-Augmented Generation for context
- **MCP Server** (`mcp_server.py`): Model Context Protocol implementation
- **GUI** (`gui.py`): PyQt6 graphical interface

## Development

### Setting up Development Environment

1. Install development dependencies:
```bash
uv sync --dev
```

2. Install pre-commit hooks:
```bash
pre-commit install
```

### Project Structure

```
├── main.py              # Main entry point
├── llm_engine.py        # LLM inference engine
├── rag.py              # RAG implementation
├── mcp_server.py      # MCP server
├── gui.py              # GUI interface
├── build.py            # Build utilities
├── models/             # Model storage
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

**Model Loading Errors**: Ensure your model files are in the correct ONNX format and placed in the `models/` directory.

**Dependency Issues**: Make sure all dependencies are installed using `uv sync`.

**GUI Not Starting**: Ensure PyQt6 is properly installed and your display environment supports GUI applications.

**MCP Server Connection**: Verify the server is running and accessible on the expected port.

### Getting Help

- Check the generated logs for detailed error information
- Use the `--verbose` flag for additional debugging output
- Ensure your Python version meets the minimum requirements (3.12+)

## Changelog

### v0.1.0
- Initial release
- NPU acceleration support
- CLI and GUI interfaces
- MCP server integration
- Repository analysis and documentation generation
