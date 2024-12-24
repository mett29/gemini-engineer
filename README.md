# Gemini Engineer

Development still in progress ...

## Description

Inspired by the great [claude-engineer](https://github.com/Doriandarko/claude-engineer/tree/main).

An AI assistant built upon the new Gemini 2.0 Flash to allow for real-time audio and text interaction.

Tested on WSL2 Ubuntu 20.04

## Installation

```bash
sudo apt install libasound2-plugins

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/mett29/gemini-engineer.git
cd gemini-engineer
uv venv
source .venv/bin/activate

# Run web interface
python main.py
```

You can also directly run the CLI:

```bash
python src/gemini_engineer.py
```