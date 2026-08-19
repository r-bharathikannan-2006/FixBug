import ctypes
from ctypes import wintypes
import re

class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT),
                ("Y", wintypes.SHORT)]

class SMALL_RECT(ctypes.Structure):
    _fields_ = [("Left", wintypes.SHORT),
                ("Top", wintypes.SHORT),
                ("Right", wintypes.SHORT),
                ("Bottom", wintypes.SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", wintypes.WORD),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]

# Windows API Constants
STD_OUTPUT_HANDLE = -11
INVALID_HANDLE_VALUE = -1

class CMD_handle:
    
    def get_last_command_output_and_width(self) -> tuple[dict, str]:
        """
        Parses the Windows Console screen buffer to extract the preceding command and its standard output.

        Args:
            self (CMD_handle): The instance reference.

        Returns:
            tuple[dict, str]: A tuple containing a dictionary of parsed command metadata (cwd, command, venv, raw) and the standard output string.
        """

        def get_entire_terminal_output() -> list[str]:
            """
            Reads the text contents of the Windows Console screen buffer from the origin to the current cursor coordinate.

            Args:
                None

            Returns:
                list[str] | tuple[list[str], int]: A list of parsed console line strings on success, or a tuple containing an error message list and an error integer on failure.
            """
            kernel32 = ctypes.windll.kernel32
            
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            if handle == INVALID_HANDLE_VALUE:
                return ["Error: Failed to get console handle."], -1

            csbi = CONSOLE_SCREEN_BUFFER_INFO()
            if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)) == 0:
                return ["Error: Failed to get console screen buffer info."], -1

            width = csbi.dwSize.X
            
            # The buffer might be allocated for 9000 lines, but we only want to read 
            # up to where the cursor currently is to avoid printing thousands of empty lines.
            max_y = csbi.dwCursorPosition.Y 
            
            buffer = ctypes.create_unicode_buffer(width)
            chars_read = wintypes.DWORD(0)
            
            lines = []

            # Loop from the absolute top of the terminal buffer down to the current line
            for y in range(max_y + 1):
                start_coord = COORD(0, y)
                
                success = kernel32.ReadConsoleOutputCharacterW(
                    handle,
                    buffer,
                    width,
                    start_coord,
                    ctypes.byref(chars_read)
                )
                
                if success != 0:
                    # .rstrip() removes the blank spaces padding the right side of the window
                    lines.append(buffer.value.rstrip())

            # Join the array of lines back into a single giant string
            return lines

        def is_prompt(line: str) -> bool:
            """
            Evaluates whether a given string matches standard OS terminal prompt regex patterns.

            Args:
                line (str): The console string line to evaluate.

            Returns:
                bool: True if the string matches a known prompt pattern, False otherwise.
            """
            line = line.strip()
            
            prompt_pattern = re.compile(
                r'^(?:\([\w.-]+\)\s*)?'          # OPTIONAL: Matches (venv) or (base) with trailing spaces
                r'(?:'                           # Grouping for the OS-specific patterns below
                r'(?:PS\s+)?(?:[a-zA-Z]:\\|/)[^>]*>'      # Windows CMD / PowerShell
                r'|'                                      # OR
                r'\[?[\w\.-]+@[\w\.-]+\]?[ :].*?[\$#%]'   # Unix/Linux/macOS (Bash/Zsh)
                r')'
            )
            
            return bool(prompt_pattern.search(line))

        def extract_cwd(prompt_line: str) -> dict:
            """
            Parses a terminal prompt string to extract the execution context and command data.

            Args:
                prompt_line (str): The raw terminal prompt string to parse.

            Returns:
                dict: A dictionary mapped with 'cwd', 'command', 'venv', and 'raw' keys representing the parsed prompt state.
            """
            prompt_line = prompt_line.strip()
            
            # Check for optional virtualenv prefix e.g. "(venv) "
            venv_match = re.match(r'^(\([^)]+\))\s*', prompt_line)
            venv = venv_match.group(1) if venv_match else None
            cleaned_line = prompt_line[len(venv_match.group(0)):] if venv_match else prompt_line
            
            # Common terminal prompt patterns
            patterns = [
                # Windows CMD / PowerShell: D:\Path\To\Dir> or PS C:\Path\To\Dir>
                r'^(?:PS\s+)?([a-zA-Z]:\\[^>#$%\n]*)\s*[>#$%]\s*(.*)$',
                
                # Git Bash: user@host MINGW64 /d/Path/To/Dir (main)$
                r'^[^\s]+\s+[^\s]+\s+(/[^($]+)(?:\s+\([^)]+\))?\s*[$#%]\s*(.*)$',
                
                # Unix/Linux/macOS Bash/Zsh: user@hostname:/path/to/dir$ or user@hostname:~/dir#
                r'^(?:[^\s:]+:)?((?:~|/)[^#$%\n]*)\s*[$#%]\s*(.*)$',
                
                # Simple path ending with symbol: /path/to/dir % command or ~/path > command
                r'^((?:[a-zA-Z]:\\|~|/)[^>#$%\n]*)\s*[>#$%]\s*(.*)$'
            ]
            
            for pattern in patterns:
                match = re.match(pattern, cleaned_line)
                if match:
                    cwd = match.group(1).strip()
                    command = match.group(2).strip()
                    return {
                        "cwd": cwd,
                        "command": command,
                        "venv": venv,
                        "raw": prompt_line
                    }
            
            return {
                "cwd": None,
                "command": prompt_line,
                "venv": venv,
                "raw": prompt_line
            }

        lines= get_entire_terminal_output()
        prompt_indices = []
        for i in range(len(lines)):
            if is_prompt(lines[i]):
                prompt_indices.append(i)

        if len(prompt_indices)<2:
            return "No previous command found in the terminal output.", "", -1

        current_prompt_index = prompt_indices[-1]
        previous_prompt_index = prompt_indices[-2]

        previous_command = lines[previous_prompt_index]
        output_lines = lines[previous_prompt_index + 1:current_prompt_index]
        # Reverse iterate to find the last command prompt
        return extract_cwd(previous_command), "\n".join(output_lines).rstrip() if output_lines else "No output found for the last command."