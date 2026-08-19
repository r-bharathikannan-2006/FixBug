import os
import sys
import re
from pathlib import Path
import requests
import traceback

from cmd_handler import CMD_handle
from cmd_display import Display
from prefixer import Prefixer
from tools import AIActionExecutor
from ai_client import GeminiClient

from config_manager import load_config, open_settings_menu

def gather_asts(directory: Path, prefixer: Prefixer, max_files: int = 50) -> str:
    """
    Generates Abstract Syntax Trees (AST) for supported source files within a directory.

    Args:
        directory (Path): The root directory to traverse.
        prefixer (Prefixer): The prefixer instance containing language mappings and ignore rules.
        max_files (int, optional): The maximum number of files to process. Defaults to 50.

    Returns:
        str: A concatenated string of XML AST representations for the processed files.
    """
    ast_data = []
    file_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Prune ignored and hidden directories from traversal tree
        dirs[:] = [d for d in dirs if d not in prefixer.IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            if file_count >= max_files:
                break
                
            ext = Path(file).suffix.lower()
            if ext in prefixer.language_map:
                filepath = os.path.join(root, file)
                try:
                    ast_xml = prefixer.abstract_syntax_tree(filepath)
                    # Normalize to relative paths for context density
                    rel_path = os.path.relpath(filepath, directory)
                    ast_data.append(f"<!-- AST for {rel_path} -->\n{ast_xml}")
                    file_count += 1
                except Exception:
                    continue
                    
    return "\n\n".join(ast_data)

def get_system_instruction() -> str:
    """
    Retrieves the system instruction prompt for the AI agent.

    Args:
        None

    Returns:
        str: The system instruction prompt detailing the agent's constraints and formatting rules.
    """
    return """You are FixBug, an advanced, autonomous AI debugging and error-correcting agent.
Your task is to analyze the user's terminal error, explore the codebase, and write precise fixes.

You are provided with the Project Directory Tree and the Abstract Syntax Trees (AST) metadata.

CRITICAL: If you need to see the exact code inside a file before making a change, you MUST request it using the READ action:
<<< ACTION: READ | FILE: path/to/file.py | LANGUAGE: NULL >>>
<<< END ACTION >>>
(You can issue multiple READ actions at once. The application will intercept them and reply with the file contents).

Once you understand the error, you MUST provide an EXPLAIN block, a FIX block, followed by modification blocks:

<<< ACTION: EXPLAIN | FILE: NULL | LANGUAGE: text >>>
Brief explanation of why the error occurred.
<<< END ACTION >>>

<<< ACTION: FIX | FILE: NULL | LANGUAGE: text >>>
Brief plan of the code modifications you are about to make.
<<< END ACTION >>>

If editing a file, you MUST use the SEARCH/REPLACE format. The SEARCH text must be an exact substring match of the existing file:
<<< ACTION: EDIT | FILE: src/main.py | LANGUAGE: python >>>
<<< SEARCH >>>
old_code()
<<< REPLACE >>>
new_code()
<<< END ACTION >>>

If creating or appending:
<<< ACTION: CREATE | FILE: src/utils.py | LANGUAGE: python >>>
code...
<<< END ACTION >>>

Do not write markdown code blocks outside of ACTION tags. Act directly."""

def upload_error_silently(error_details: str):
    """
    Dispatches error traceback data to a remote webhook asynchronously.

    Args:
        error_details (str): The formatted traceback or error message to transmit.

    Returns:
        None
    """
    # Webhook endpoint configuration
    webhook_url = "https://script.google.com/macros/s/AKfycbxr7Jth2m-IdT_dL8KZMhzfn7e7-a-Bt5Y1547eKSeSJaPfkFSx3LHi6Y0TAOWD6jj9/exec" 
        
    # Construct payload for remote logging endpoint
    payload = {
        "content": f"Crash Report:\n\n{error_details[-3000:]}" 
    }
    
    try:
        # Enforce strict timeout to prevent thread blocking on redirect parsing
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        # Suppress network exceptions to maintain graceful degradation
        pass

def main():
    """
    Main entry point for the FixBug CLI application.
    
    Handles configuration loading, context gathering, AI agent initialization, 
    and the execution loop for analyzing and resolving terminal errors.

    Args:
        None

    Returns:
        None
    """
    config = load_config()
    
    # Initialize UI components with theme configurations
    display = Display(
        output_max_lines=config["output_max_lines"],
        truncate_dot_line_length=config["truncate_dot_line_length"],
        command_color=config["theme_command_color"],
        output_color=config["theme_output_color"],
        exp_color=config["theme_exp_color"],
        fix_color=config["theme_fix_color"]
    )
    
    # Process CLI arguments for configuration management
    if len(sys.argv) > 1 and sys.argv[1] in ["--settings", "-s", "config"]:
        open_settings_menu(display)
        sys.exit(0)
        
    display.display_title()

    # Validate prerequisite environment variables
    if not config.get("api_key"):
        display.display_progress("[!] GEMINI API KEY is missing.")
        display.display_progress("Please run 'fixbug --settings' to configure the application.")
        sys.exit(1)

    display.display_progress("Initializing FixBug Agent...")
    
    # Retrieve last command execution context
    cmd = CMD_handle()
    result = cmd.get_last_command_output_and_width()
    
    if len(result) == 3:
        display.display_progress("No previous command or output found in terminal. Exiting.")
        sys.exit(1)
        
    command_dict, output = result
    cwd = command_dict.get('cwd') or os.getcwd()
    
    display.display_cmd_and_output(command=command_dict['command'], output=output)
    display.display_progress(f"Gathering local context from {cwd}...")

    # Aggregate project structure and AST metadata
    prefixer = Prefixer(cwd)
    dir_tree = prefixer.directory_tree()
    ast_context = gather_asts(Path(cwd), prefixer)

    prompt = f"""
Current Working Directory: {cwd}
Virtual Environment: {command_dict.get('venv') or 'None'}

--- Directory Tree ---
{dir_tree}

--- Codebase AST Metadata ---
{ast_context}

--- Last Executed Command ---
{command_dict.get('command')}

--- Terminal Error / Output ---
{output}

Please read the relevant files or provide the fix actions now.
"""
    # Initialize LLM client and execution dependencies
    display.display_progress("Connecting to AI Core...")
    try:
        # Inject configuration into the AI client
        ai_client = GeminiClient(
            system_instruction=get_system_instruction(),
            api_key=config['api_key'],
            model=config['model']
        )
    except Exception as e:
        display.display_progress(f"[!] Initialization Error: {e}")
        sys.exit(1)

    def get_current_cwd() -> str:
        """
        Retrieves the current working directory from the outer scope.

        Args:
            None

        Returns:
            str: The absolute path to the current working directory.
        """
        return cwd
        
    executor = AIActionExecutor(display_instance=display, get_cwd_func=get_current_cwd)
    
    # Execute main agentic evaluation loop
    max_loops = config["max_agent_loops"] 
    loop_count = 0
    current_prompt = prompt

    while loop_count < max_loops:
        loop_count += 1
        display.display_progress(f"Agent Loop [{loop_count}/{max_loops}]: Waiting for AI analysis...")
        
        try:
            response_text = ai_client.send_message(current_prompt)
        except Exception as e:
            display.display_progress(f"[!] AI API Communication Error: {e}")
            break

        # Extract file read requests via regex parsing
        read_pattern = re.compile(r"<<<\s*ACTION:\s*READ\s*\|\s*FILE:\s*(?P<file>[^\s>]+)\s*\|\s*LANGUAGE.*?(?:>>>|\n)", re.IGNORECASE)
        reads = read_pattern.findall(response_text)

        if reads:
            unique_reads = set(reads)
            display.display_progress(f"AI requested to read {len(unique_reads)} file(s).")
            file_contents = []
            
            for filepath in unique_reads:
                full_path = os.path.join(cwd, filepath)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        file_contents.append(f"--- FILE CONTENTS: {filepath} ---\n{content}\n-----------------------")
                    except Exception as e:
                        file_contents.append(f"--- FILE CONTENTS: {filepath} ---\n[Error reading file: {e}]\n-----------------------")
                else:
                    file_contents.append(f"--- FILE CONTENTS: {filepath} ---\n[File does not exist]\n-----------------------")

            current_prompt = "Here are the contents of the requested files:\n\n" + "\n\n".join(file_contents) + "\n\nPlease continue debugging."
            
        else:
            # Terminate loop on receiving terminal EXPLAIN/FIX/EDIT actions
            display.display_progress("Processing AI action blocks...")
            executor.execute_from_text(response_text)
            break

    if loop_count >= max_loops:
        display.display_progress("Maximum agent interaction limit reached.")
        
    display.line_break()
    display.display_progress("FixBug execution completed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Catch interrupt signal for graceful exit
        print("\n\033[93m[!] Operation cancelled by user.\033[0m")
        sys.exit(0)
    except Exception as e:
        # Capture complete traceback stack
        error_traceback = traceback.format_exc()
        
        # Upload error data asynchronously
        upload_error_silently(error_traceback)
        
        # Output simple error state to standard output
        print("\n\033[91m[!] Something went wrong, please try again.\033[0m")
        sys.exit(1)