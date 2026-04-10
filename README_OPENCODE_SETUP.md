# CORAL + OpenCode Setup Guide

This guide explains how to set up CORAL with the OpenCode orchestrator and run the Circle Packing example using Google's Gemini models. It covers both local (non-Docker) and Docker-based execution.

## Prerequisites

- **Python 3.12+**
- **Node.js 20+** (Required for OpenCode)
- **uv** (Fast Python package installer and resolver)
- **Docker or Podman** (Optional but highly recommended for isolated agent environments. Podman is a 100% compatible drop-in replacement for Docker. If you don't have either installed, you can still run the agents locally!)

## 1. Install OpenCode

OpenCode is the autonomous agent orchestrator that CORAL uses to solve tasks.

You can install the standard version or the "slim" version (which has fewer dependencies if you don't need the full browser automation suite).

**Standard Install:**
```bash
npm install -g opencode-ai@latest
```

**Slim Install (Recommended for basic CORAL usage):**
```bash
npm install -g opencode-ai-slim@latest
```
*(Note: If you use the slim version, ensure your system path recognizes the `opencode` command, or alias it if necessary).*

## 2. Set Up CORAL

Navigate to the CORAL repository and install its dependencies using `uv`.

```bash
# Navigate to the CORAL directory
cd CORAL

# Install dependencies and the coral CLI
uv sync
```

## 3. Configure Gemini API Key

CORAL and OpenCode need your Gemini API key to communicate with the models.

Create a `.env` file in the root of the `CORAL` directory:

```bash
echo "GEMINI_API_KEY=your_actual_api_key_here" > .env
```

## 4. Running the Circle Packing Example

The Circle Packing example challenges the agent to pack 26 circles into a unit square to maximize the sum of their radii.

### Option A: Local Execution (Non-Docker)

Running locally means the agent will execute code directly on your host machine. This is perfect if you don't have Docker installed, but be aware that the agent has access to your local file system.

1. **Configure the task:** Ensure `examples/circle_packing/task.yaml` has `session: local`.
2. **Run CORAL:**
   ```bash
   # Load the environment variables and start CORAL
   set -a && source .env && set +a
   uv run coral start -c examples/circle_packing/task.yaml
   ```

### Option B: Docker Execution (Recommended)

Running in Docker isolates the agent's code execution, preventing it from accidentally modifying your host system.

1. **Configure the task:** Ensure `examples/circle_packing/task.yaml` has `session: docker`.
2. **Build the Docker Image:**
   ```bash
   # The SETUPTOOLS_SCM_PRETEND_VERSION is needed if building without the .git folder
   ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0
   docker build -f docker/opencode/Dockerfile -t coral-opencode:local .
   ```
3. **Run CORAL:**
   ```bash
   # Load the environment variables and start CORAL
   set -a && source .env && set +a
   SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 uv run coral start -c examples/circle_packing/task.yaml
   ```

## 5. Monitoring the Run

If you have `ui: true` set in your `task.yaml`, CORAL will automatically start a web dashboard.

Open your browser and navigate to:
👉 **http://localhost:8420**

Here you can watch the agents' logs, see their current scores, and monitor their progress in real-time!

## Troubleshooting

- **Docker API Key Issues:** If the agent inside Docker complains about missing API keys, ensure you are sourcing the `.env` file *before* running `coral start`, as the CLI forwards `*_API_KEY` variables to the container.
- **Port Conflicts:** If port 8420 is already in use, you can stop the existing container using `docker stop <container_name>` or `coral stop`.
- **UI Not Accessible:** If running in Docker and the UI is not accessible from your host, ensure `coral/cli/ui.py` binds the server to `0.0.0.0` instead of `127.0.0.1`.
