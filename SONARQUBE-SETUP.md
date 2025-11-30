# SonarQube & SonarLint Setup Guide

## Status

- **Java 17**: ✅ Installed (`openjdk-17-jre`)
- **SonarLint VSCode Extension**: ✅ Installed (`sonarsource.sonarlint-vscode`)
- **SonarScanner CLI**: ✅ Installed (v7.3.0.5189)

## SonarLint VSCode Extension

The SonarLint extension is already installed and should now be working.

### Configuration

SonarLint will automatically analyze your Python code as you type. To customize settings:

1. Open VSCode Settings (Ctrl+,)
2. Search for "SonarLint"
3. Adjust rules and behavior as needed

Or edit `.vscode/settings.json`:
```json
{
  "sonarlint.rules": {
    "python:S1192": {
      "level": "on"
    }
  },
  "sonarlint.output.showAnalyzerLogs": true
}
```

### Verify It's Working

1. Open any Python file in VSCode
2. Look for SonarLint warnings/errors underlined in your code
3. Check the "Problems" panel (Ctrl+Shift+M)

## SonarScanner CLI

SonarScanner CLI is installed at `~/.local/sonar-scanner/`

### Using SonarScanner

To run a scan on this project:

```bash
# Reload your shell to get updated PATH
source ~/.bashrc

# Run scan from project directory
cd ~/dev/.claude
~/.local/sonar-scanner/bin/sonar-scanner
```

Or use the full path:
```bash
~/.local/sonar-scanner/bin/sonar-scanner
```

### Project Configuration

The project is configured in [sonar-project.properties](sonar-project.properties):

- **Project Key**: `claude-config`
- **Sources**: `src/`
- **Python Version**: 3.12
- **Exclusions**: `__pycache__`, `.venv`, `tmp_cleanup`, etc.

### SonarQube Server

**Note**: SonarScanner CLI requires a SonarQube server to send results to. You have two options:

1. **SonarQube Cloud** (Free for public projects)
   - Sign up at: https://sonarcloud.io
   - Generate a token
   - Add to scan command:
     ```bash
     ~/.local/sonar-scanner/bin/sonar-scanner \\
       -Dsonar.token=YOUR_TOKEN \\
       -Dsonar.organization=YOUR_ORG
     ```

2. **Local SonarQube Server** (For private analysis)
   ```bash
   # Run SonarQube in Docker
   docker run -d --name sonarqube -p 9000:9000 sonarqube:community

   # Access at http://localhost:9000
   # Default credentials: admin/admin

   # Scan command
   ~/.local/sonar-scanner/bin/sonar-scanner \\
     -Dsonar.host.url=http://localhost:9000 \\
     -Dsonar.token=YOUR_LOCAL_TOKEN
   ```

3. **Standalone Analysis** (No server - limited)
   - SonarLint extension provides standalone analysis without a server
   - CLI requires a server for full functionality

## Environment Setup

Your `~/.bashrc` has been updated with:

```bash
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$HOME/.local/sonar-scanner/bin:$PATH"
```

Reload your shell:
```bash
source ~/.bashrc
```

## Integration with Existing Tools

This project already has excellent code quality tools:
- **Ruff**: PyStrict-aligned linting
- **BasedPyright**: Strict type checking
- **Bandit**: Security scanning
- **Pre-commit hooks**: Automated checks

SonarScanner adds:
- Code smell detection
- Duplication analysis
- Technical debt tracking
- Centralized quality dashboard (if using SonarQube server)

## Quick Commands

```bash
# Check SonarScanner version
~/.local/sonar-scanner/bin/sonar-scanner --version

# Run scan (requires SonarQube server)
~/.local/sonar-scanner/bin/sonar-scanner -Dsonar.token=YOUR_TOKEN

# Debug mode
~/.local/sonar-scanner/bin/sonar-scanner -X
```

## Cleanup

Downloaded archive has been left in place:
```bash
# Optional: Remove download to save space
rm ~/dev/.claude/sonar-scanner-cli-7.3.0.5189-linux-x64.zip
```

## Resources

- [SonarLint VSCode Extension](https://marketplace.visualstudio.com/items?itemName=SonarSource.sonarlint-vscode)
- [SonarScanner CLI Documentation](https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/scanners/sonarscanner)
- [SonarQube Cloud](https://sonarcloud.io)
- [SonarScanner Releases](https://github.com/SonarSource/sonar-scanner-cli/releases)
