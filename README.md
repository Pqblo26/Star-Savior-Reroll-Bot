# Star Savior Reroll Bot

Automated reroll bot for Star Savior using Python + ADB + MuMu Player 12.

## Features
- Automatically completes the full tutorial from start
- Performs 5 multi-pulls on banner1 and 6 single pulls on banner2
- Detects SSR characters using template matching (OpenCV)
- Stops automatically when a configured objective is met
- Supports multiple parallel instances
- Saves state on exit to resume from the same step

## Requirements
- Python 3.10+
- MuMu Player 12 with ADB enabled
- `pip install opencv-python numpy`

## Usage
```bash
python bot.py
```

## Configuration
Edit `config.json` to set your device IDs, player name and starting step.

Character templates go in the `templates/` folder. Use `recorder.py` to capture them and `debug_template.py` to verify detection confidence.
