#!/bin/bash
# ~/.local/bin/launch_sticky.sh

# Ensure the Alacritty config exists (for your minimalist theme)
ALACRITTY_CONFIG="$HOME/.config/alacritty/kanban_alacritty.toml"

# Launch alacritty pointing to your sync script
alacritty --config-file "$ALACRITTY_CONFIG" -e "$HOME/.venvs/kanban/bin/python3" "$HOME/.local/bin/journal_sync.py"
