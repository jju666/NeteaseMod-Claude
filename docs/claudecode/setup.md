# Claude Code Setup Documentation

## System Requirements

The documentation specifies that Claude Code requires:
- **OS**: macOS 10.15+, Ubuntu 20.04+/Debian 10+, or Windows 10+ with WSL or Git Bash
- **Hardware**: 4GB+ RAM minimum
- **Software**: Node.js 18+ for NPM installations
- **Network**: Internet access for authentication and AI processing
- **Shell**: Bash, Zsh, or Fish preferred
- **Location**: Must be in an "Anthropic supported country/region"

## Installation Methods

Three primary installation approaches are described:

1. **Native Installation (Recommended)**: Self-contained executable with no Node.js dependency, offering improved auto-update stability
2. **NPM Installation**: For environments preferring Node.js package management
3. **Local Installation**: Moving from NPM global to local installation to avoid permission issues

The documentation warns users: "Do not use `sudo npm install -g`" due to potential permission problems and security risks.

## Authentication Options

Three authentication paths are available:
- Claude Console with OAuth (requires active billing at console.anthropic.com)
- Claude App Pro/Max subscription plans
- Enterprise platforms via Amazon Bedrock or Google Vertex AI

## Key Features

The setup guide mentions automatic updates occur during startup and runtime, with notifications when updates install. Users can disable automatic updates through the `DISABLE_AUTOUPDATER` environment variable.

After installation, users navigate to their project directory and launch the tool using the `claude` command.
