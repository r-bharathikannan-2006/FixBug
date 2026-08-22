import json
import os
from pathlib import Path

# Set configuration directory and file paths
CONFIG_DIR = Path.home() / "FixBug-core"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini-3.6-flash",
    "max_agent_loops": 5,
    "output_max_lines": 6,
    "truncate_dot_line_length": 3,
    "theme_command_color": "\x1b[38;2;253;247;161m",
    "theme_output_color": "\x1b[38;2;224;119;123m",
    "theme_exp_color": "\x1b[38;2;253;247;161m",
    "theme_fix_color": "\x1b[38;2;253;247;161m"
}

def load_config() -> dict:
    """
    Load user configuration from disk.
    
    Args:
        None
        
    Returns:
        dict: Current configuration merged with defaults.
    """
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Merge with default configuration keys
            return {**DEFAULT_CONFIG, **user_config}
    except Exception:
        return DEFAULT_CONFIG

def save_config(config_data: dict):
    """
    Write configuration data to disk.
    
    Args:
        config_data (dict): Configuration dictionary to persist.
        
    Returns:
        None
    """
    # Create directory if missing
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

def open_settings_menu(display):
    """
    Render and handle interactive settings interface.
    
    Args:
        display (object): Display handler instance for user interface rendering.
        
    Returns:
        None
    """
    import sys  # Import sys for stdout operations
    config = load_config()
    display._get_width()
    safe_width = display.printable_width + 4

    # Print menu headers
    print() 
    display.display_title()
    print(f"\n {display.command_color}{' FIXBUG SETTINGS MENU ': ^{safe_width}}\033[0m")
    print(f" {' Use Up/Down Arrows and Enter to Select ': ^{safe_width}}\n")
    print(f"╭{'─' * (safe_width - 2)}╮")

    # Initialize line tracker
    lines_to_go_up = 0

    while True:
        # Clear previous console output
        if lines_to_go_up > 0:
            for _ in range(lines_to_go_up):
                # Execute ANSI cursor control
                sys.stdout.write("\033[1A\033[2K\r")
            sys.stdout.flush()

        # Obfuscate API key
        api_key = config.get('api_key', '')
        masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "Not Set"

        options = [
            f"1. API Key                 : {masked_key}",
            f"2. AI Model                : {config['model']}",
            f"3. Max Agent Loops         : {config['max_agent_loops']}",
            f"4. Output Max Lines        : {config['output_max_lines']}",
            f"5. Truncate Dot Length     : {config['truncate_dot_line_length']}",
            "6. Save and Exit",
            "7. Exit Without Saving"
        ]

        selected = display.display_options(options, safe_width)
        
        # Calculate options box line count
        lines_to_go_up = len(options) + 1

        if selected.startswith("6"):
            save_config(config)
            print("\n  \033[92mSettings saved successfully.\033[0m\n")
            break
        elif selected.startswith("7"):
            print("\n  \033[91mSettings discarded.\033[0m\n")
            break
        elif selected.startswith("1"):
            print(f"\n  Current API Key: {api_key}")
            new_key = input("  Enter new API Key (leave blank to cancel): ").strip()
            if new_key: config['api_key'] = new_key
            # Increment line count for input prompt
            lines_to_go_up += 3  
        elif selected.startswith("2"):
            models = ["gemini-3.6-flash", "gemini-3.6-pro", "gemini-2.5-flash", "Cancel"]
            print(f"\n  {display.exp_color}{' SELECT AI MODEL ': ^{safe_width}}\033[0m")
            print(f"╭{'─' * (safe_width - 2)}╮")
            mod_sel = display.display_options(models, safe_width)
            if mod_sel != "Cancel": config['model'] = mod_sel
            # Increment line count for submenu elements
            lines_to_go_up += 3 + len(models) + 1  
        elif selected.startswith("3"):
            print()
            new_val = input("  Enter max loops (e.g., 5): ").strip()
            if new_val.isdigit(): config['max_agent_loops'] = int(new_val)
            lines_to_go_up += 2
        elif selected.startswith("4"):
            print()
            new_val = input("  Enter output max lines (e.g., 6): ").strip()
            if new_val.isdigit(): config['output_max_lines'] = int(new_val)
            lines_to_go_up += 2
        elif selected.startswith("5"):
            print()
            new_val = input("  Enter truncate dot length (e.g., 3): ").strip()
            if new_val.isdigit(): config['truncate_dot_line_length'] = int(new_val)
            lines_to_go_up += 2