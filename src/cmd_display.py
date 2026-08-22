import os
import sys
import re
import difflib
from colorama import init
import textwrap
from cfonts import say
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer, guess_lexer
from pygments.formatters import Terminal256Formatter
from pygments.util import ClassNotFound
import unicodedata
from cmd_handler import CMD_handle
from general import folder_validation

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
RESET_COLOR = "\033[0m"

class Display:
    """
    Handles terminal-based UI rendering, formatting, and diff visualizations.
    """
    def __init__(
            self, 
            output_max_lines: int=6, 
            command_color: str = "\x1b[38;2;253;247;161m",
            output_color: str = "\x1b[38;2;224;119;123m",
            between_them:str = "\n", 
            at_start_and_end:str = "\n",
            truncate_dot_line_length:int = 3,
            exp_color:str = "\x1b[38;2;253;247;161m",
            fix_color:str = "\x1b[38;2;253;247;161m",
            code_box_color:str = "\x1b[38;2;253;247;161m"
        ):
        """
        Initializes the Display instance with configurable formatting constraints.

        Args:
            output_max_lines (int): Maximum permitted lines for standard output rendering.
            command_color (str): ANSI escape sequence for command styling.
            output_color (str): ANSI escape sequence for output styling.
            between_them (str): Spacer string between command and output sections.
            at_start_and_end (str): Spacer string used at block boundaries.
            truncate_dot_line_length (int): Dot length indicator for truncated blocks.
            exp_color (str): ANSI escape sequence for explanation blocks.
            fix_color (str): ANSI escape sequence for fix blocks.
            code_box_color (str): ANSI escape sequence for code visualization blocks.

        Returns:
            None
        """
        init()

        self.output_max_lines = output_max_lines
        self.command_color = command_color
        self.output_color = output_color
        self.between_them = between_them
        self.at_start_and_end = at_start_and_end
        self.truncate_dot_line_length = 3
        self.exp_color = exp_color
        self.fix_color = fix_color
        self.code_box_color = code_box_color

        self._get_width()

    def _get_width(self):
        """
        Calculates and stores the current terminal width constraints.

        Args:
            None

        Returns:
            None
        """
        try:
            term_width = os.get_terminal_size().columns
            self.width = min(term_width, 120)
        except OSError:
            self.width = 120
        
        self.printable_width = self.width - 4

    def display_title(self):
        """
        Renders the main application title.

        Args:
            None

        Returns:
            None
        """
        say("FIXBUG - CORE", font="block", colors=["#E74856"])

    def display_progress(self, message: str) -> None:
        """
        Renders a wrapped progress message to standard output.

        Args:
            message (str): The progress message to format and display.

        Returns:
            None
        """
        self._get_width()
        prefix = f"{self.command_color}[>_]{RESET_COLOR} "
        prefix_plain_len = 5 

        wrap_width = max(10, self.width - prefix_plain_len)
        lines = textwrap.wrap(message, width=wrap_width)
        
        if not lines:
            return

        print(f"{prefix}{lines[0]}")
        for line in lines[1:]:
            print(f"{' ' * prefix_plain_len}{line}")

    def display_cmd_and_output(self, command: str, output: str) -> None:
        """
        Renders an executed command and its corresponding standard output.

        Args:
            command (str): The executed command string.
            output (str): The standard output resulting from the command.

        Returns:
            None
        """
        self._get_width() 
        
        def truncate_line(lines: list[str], max_length: int) -> list[str]:
            """
            Truncates a sequence of lines to respect the maximum column width.

            Args:
                lines (list[str]): The target string sequence.
                max_length (int): Maximum allowed characters per line.

            Returns:
                list[str]: The truncated line sequence.
            """
            result = []
            safe_length = max_length - 4 
            for l in lines:
                if len(l) <= safe_length:
                    result.append(l)
                else:
                    result.append(l[:safe_length - 3] + "...")
            return result
        
        output_non_truncated = output.splitlines()
        output_non_truncated = [x for x in output_non_truncated if x.strip()]
        if len(output_non_truncated) <= self.output_max_lines:
            output_lines = truncate_line(output_non_truncated, self.printable_width)
        else:
            half = self.output_max_lines // 2
            truncated = truncate_line(output_non_truncated[:half], self.printable_width) + ["..." for i in range(self.truncate_dot_line_length)] + truncate_line(output_non_truncated[-half:], self.printable_width)
            output_lines = truncated
            
        length = self.printable_width
        
        top    = f"{self.at_start_and_end}{self.command_color}╭{' [ LAST COMMAND ] ':─^{length + 2}}╮"
        middle = f"│ {self.command_color}{command.ljust(length, ' ')} │"
        middle += f"\n╰{'─' * (length+2)}╯"
        middle += f"\n{self.between_them}"
        middle += f"{self.output_color}╭{' [ LAST OUTPUT AND ERROR ] ':─^{length + 2}}╮"
        for line in output_lines:
            middle += f"\n│ {line.ljust(length, ' ')} │"
        bottom = f"╰{'─' * (length + 2)}╯{RESET_COLOR}{self.at_start_and_end}"
        
        print(f"{top}")
        print(f"{middle}")
        print(f"{bottom}{RESET_COLOR}")

    def display_explanation(self, explanation: str):
        """
        Formats and renders diagnostic explanation text.

        Args:
            explanation (str): The explanation text body.

        Returns:
            None
        """
        self._get_width()
        explanation_lines = explanation.splitlines()
        result = []
        for text in explanation_lines:
            if not text:
                result.append(text)
            else:
                wrapped_lines = textwrap.wrap(text, width=self.printable_width)
                result.extend(wrapped_lines)
        explanation_lines = result
        length = self.printable_width
        
        top    = f"{self.exp_color}╭{' [ Explanation ] ':─^{length + 2}}╮{RESET_COLOR}"
        middle = ""
        for line in explanation_lines:
            if middle:
                middle += f"\n{self.exp_color}│ {line.ljust(length, ' ')} │{RESET_COLOR}"
            else:
                middle = f"{self.exp_color}│ {line.ljust(length, ' ')} │{RESET_COLOR}"
        bottom = f"{self.exp_color}╰{'─' * (length + 2)}╯{RESET_COLOR}"
        
        print(top)
        print(middle)
        print(bottom)
        self.new_line()

    def display_fixes(self, fixes: str):
        """
        Formats and renders the remediation plan.

        Args:
            fixes (str): The structured fix plan text.

        Returns:
            None
        """
        self._get_width()
        fixes_lines = fixes.splitlines()
        result = []
        for text in fixes_lines:
            if not text:
                result.append(text)
            else:
                wrapped_lines = textwrap.wrap(text, width=self.printable_width)
                result.extend(wrapped_lines)
        fixes_lines = result
        length = self.printable_width
        
        top    = f"{self.fix_color}╭{' [ Fix Plan ] ':─^{length + 2}}╮{RESET_COLOR}"
        middle = ""
        for line in fixes_lines:
            if middle:
                middle += f"\n{self.fix_color}│ {line.ljust(length, ' ')} │{RESET_COLOR}"
            else:
                middle = f"{self.fix_color}│ {line.ljust(length, ' ')} │{RESET_COLOR}"
        bottom = f"{self.fix_color}╰{'─' * (length + 2)}╯{RESET_COLOR}"
        
        print(top)
        print(middle)
        print(bottom)
        self.new_line()

    def compare_editing(
            self,
            file_path: str,
            editing: str,
            language: str,
            surrounding_lines: int = 3,
            diff_title: str = None,
            embed_width: int = 120
        ):
        """
        Calculates and renders a vertical diff view between original and edited source code.

        Args:
            file_path (str): Target file path.
            editing (str): The raw structural modification instructions (SEARCH/REPLACE blocks).
            language (str): Target language identifier for syntax highlighting.
            surrounding_lines (int, optional): Number of context lines to display around modifications. Defaults to 3.
            diff_title (str, optional): Title for the diff render block. Defaults to None.
            embed_width (int, optional): Boundary column width for the diff renderer. Defaults to 120.

        Returns:
            tuple: Contains the mutated content (str) and the sequence of rendered diff lines (list[str]).
        """
        if not os.path.exists(file_path):
            error_msg = f"Error: File '{file_path}' not found."
            return None, [f"│ \033[91m{error_msg.ljust(embed_width - 4)}\033[0m │"]
            
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read().replace("\t", "    ")

        editing_cleaned = re.sub(r"<<<\s*END ACTION\s*>>>", "", editing).strip()

        search_replace_pattern = re.compile(
            r"<<<\s*SEARCH\s*>>>\n?(.*?)\n?<<<\s*REPLACE\s*>>>\n?(.*?)(?=(?:<<<\s*SEARCH\s*>>>|$))",
            re.DOTALL
        )
        
        matches = search_replace_pattern.findall(editing_cleaned)

        new_content = original_content
        for search_text, replace_text in matches:
            search_text = search_text.rstrip("\r\n").replace("\t", "    ")
            replace_text = replace_text.rstrip("\r\n").replace("\t", "    ")
            
            if search_text in new_content:
                new_content = new_content.replace(search_text, replace_text, 1)
            else:
                print(f"\033[93mWarning: A SEARCH block was not found in the file.\033[0m")

        original_lines = original_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = difflib.SequenceMatcher(None, original_lines, new_lines)
        opcodes = matcher.get_opcodes()
        
        if all(op[0] == "equal" for op in opcodes):
            msg = "No changes detected."
            return new_content, [f"│ \033[94m{msg.ljust(embed_width - 4)}\033[0m │"]

        try:
            lexer = get_lexer_by_name(language.lower())
        except ClassNotFound:
            lexer = TextLexer()
        formatter = Terminal256Formatter(style="monokai")

        FG_GRAY = "\033[90m"
        FG_DEFAULT = "\033[39m"
        RESET = "\033[0m"
        BG_DARK_RED = "\033[48;5;52m"
        BG_DARK_GREEN = "\033[48;5;22m"

        vertical_rows = []
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    vertical_rows.append({
                        'l_num': i+1, 'r_num': j+1, 'text': original_lines[i],
                        'type': 'equal', 'is_change': False
                    })
            elif tag == 'replace':
                for i in range(i1, i2):
                    vertical_rows.append({
                        'l_num': i+1, 'r_num': None, 'text': original_lines[i],
                        'type': 'delete', 'is_change': True
                    })
                for j in range(j1, j2):
                    vertical_rows.append({
                        'l_num': None, 'r_num': j+1, 'text': new_lines[j],
                        'type': 'insert', 'is_change': True
                    })
            elif tag == 'delete':
                for i in range(i1, i2):
                    vertical_rows.append({
                        'l_num': i+1, 'r_num': None, 'text': original_lines[i],
                        'type': 'delete', 'is_change': True
                    })
            elif tag == 'insert':
                for j in range(j1, j2):
                    vertical_rows.append({
                        'l_num': None, 'r_num': j+1, 'text': new_lines[j],
                        'type': 'insert', 'is_change': True
                    })

        keep_indices = set()
        for idx, row in enumerate(vertical_rows):
            if row['is_change']:
                start = max(0, idx - surrounding_lines)
                end = min(len(vertical_rows), idx + surrounding_lines + 1)
                keep_indices.update(range(start, end))

        if not keep_indices:
            return new_content, []

        sorted_indices = sorted(list(keep_indices))
        chunks = []
        current_chunk = [sorted_indices[0]]
        for idx in sorted_indices[1:]:
            if idx == current_chunk[-1] + 1:
                current_chunk.append(idx)
            else:
                chunks.append(current_chunk)
                current_chunk = [idx]
        chunks.append(current_chunk)

        col_fixed_width = 14 
        target_code_width = embed_width - 2 - col_fixed_width
        
        raw_text = "\n".join([(vertical_rows[i]['text'] if vertical_rows[i]['text'] is not None else "") for i in sorted_indices])
                 
        hl_text = highlight(raw_text, lexer, formatter).splitlines()
        hl_text += [""] * (len(sorted_indices) - len(hl_text))
        
        diff_lines_out = []
        global_idx = 0
        
        for chunk_idx, chunk in enumerate(chunks):
            if chunk_idx > 0:
                diff_lines_out.append(f"{FG_GRAY}│{' ' * (embed_width-2)}│{RESET}")
            for orig_idx in chunk:
                row = vertical_rows[orig_idx]
                                 
                bg = BG_DARK_RED if row['type'] == 'delete' else (BG_DARK_GREEN if row['type'] == 'insert' else "")
                sign = "-" if row['type'] == 'delete' else ("+" if row['type'] == 'insert' else " ")
                l_num = f"{row['l_num']:4d}" if row['l_num'] is not None else "    "
                r_num = f"{row['r_num']:4d}" if row['r_num'] is not None else "    "
                
                raw_code = hl_text[global_idx]
                
                visible_text = ANSI_ESCAPE.sub('', raw_code)
                visible_len = 0
                for char in visible_text:
                    if unicodedata.east_asian_width(char) in ('W', 'F'):
                        visible_len += 2
                    else:
                        visible_len += 1
                
                padding_spaces = " " * max(0, target_code_width - visible_len)
                
                code = raw_code.replace("\033[0m", f"\033[0m{bg}")
                
                inner = f"{bg} {FG_GRAY}{l_num} {r_num} {sign}|{FG_DEFAULT} {code}{padding_spaces}{RESET}"
                                 
                diff_lines_out.append(f"{FG_GRAY}│{RESET}{inner}{FG_GRAY}│{RESET}")
                global_idx += 1
                
        return new_content, diff_lines_out

    
    def display_action_info(
            self,
            action_number: int,
            action_name: str,
            file_path: str,
            content: str,
            description: str,
            language: str, 
            total_actions: int,
            fn_get_cwd: str,
            del_details: str=None,
        ) -> str:
        """
        Coordinates the interactive execution state prompt for a file action.

        Args:
            action_number (int): Sequential ID of the current action.
            action_name (str): Action type literal (e.g., CREATE, EDIT).
            file_path (str): Path of the target file.
            content (str): Content payload associated with the action.
            description (str): Functional description of the execution step.
            language (str): Target language identifier.
            total_actions (int): Aggregate total of pending actions.
            fn_get_cwd (str): Current working directory lookup handler.
            del_details (str, optional): Detailed output for deletion requests. Defaults to None.

        Returns:
            str: Selected user action instruction string.
        """
        self._get_width()

        def format_detail_box(prefix: str, description: str, box_width: int) -> str:
            """
            Formats detail arrays into bounded text representations.

            Args:
                prefix (str): Text prefix mapping.
                description (str | list): Detail data block.
                box_width (int): Calculated box column width.

            Returns:
                str: Formatted text sequence spanning multiple lines.
            """
            if isinstance(description, list):
                description = " ".join(str(item) for item in description)
            elif not description:
                description = ""
            elif not isinstance(description, str):
                description = str(description)

            blank_prefix = " " * len(prefix) 
            text_width = max(1, box_width - 2 - len(prefix))
            
            lines = textwrap.wrap(description, width=text_width) or [""]
            middle = ""
            
            for i, line in enumerate(lines):
                padded_text = line.ljust(text_width)
                if i == 0:
                    middle += f"│{prefix}{padded_text}│\n"
                else:
                    middle += f"│{blank_prefix}{padded_text}│\n"
            return middle
            
        action_name = action_name.upper()
        description = description.splitlines()

        action_title_map = {
            'CREATE': '\U0001F4DD ACTION REQUESTED : CREATE FILE',
            'APPEND': '\U0001f795 ACTION REQUESTED : APPEND FILE',
            'DELETE': '\u26a0\ufe0f ACTION REQUESTED : DELETE FILE',
            'EDIT': '\U0001F58A ACTION REQUESTED : EDIT FILE',
        }

        preview_title_map = {
            'CREATE': f"Preview (+{len(content.splitlines())} lines) : ",
            'APPEND': f"Addition (+{len(content.splitlines())} lines at EOF) : ",
            'EDIT': f"Diff (Red, Green):",
            'DELETE': None
        }

        show_full_preview = False

        while True:
            safe_width = self.printable_width + 4
            top = f"╭{'':─^{safe_width-2}}╮\n"
            middle = ""
            
            action_title = action_title_map.get(action_name, 'ACTION')
            action_count = f"{str(action_number).rjust(2, ' ')}/{str(total_actions).ljust(2, ' ')}"
            
            middle += f"│ {action_count} {action_title.ljust((safe_width-(11 if not action_name=='DELETE' else 10)), ' ')} │\n"
            middle += f"├{'':─^{safe_width-2}}┤\n"
            middle += format_detail_box(" Path        : ", ('./' + file_path) if folder_validation(file_path, fn_get_cwd) else file_path, safe_width)
            middle += format_detail_box(" Description : ", description, safe_width)
            
            if action_name == 'DELETE' and del_details:
                middle += format_detail_box(" Status      : ", del_details, safe_width)
                
            middle += f"├{'':─^{safe_width-2}}┤\n"
            
            if action_name in ['CREATE', 'APPEND']:
                content_lst = [line for line in content.splitlines() if line]
                total_lines = len(content_lst)
                
                if show_full_preview:
                    title_text = f"Full Preview of {total_lines} lines :"
                else:
                    title_text = preview_title_map[action_name]
                    
                middle += f"│ {title_text.ljust(safe_width -4, ' ')} │\n"
                
                if content_lst:
                    lines_to_show = content_lst if show_full_preview else content_lst[:5]
                    code_to_highlight = "\n".join(lines_to_show)
                    wrap_width = safe_width - 4
                    
                    coloured_code_lines = self.print_highlighted_code(
                        code_string=code_to_highlight, 
                        file_path=file_path, 
                        language_name=language, 
                        inside_box=False, 
                        width=wrap_width
                    )
                    
                    for colored_line in coloured_code_lines:
                        visible_text = ANSI_ESCAPE.sub('', colored_line)
                        visible_len = 0
                        for char in visible_text:
                            if unicodedata.east_asian_width(char) in ('W', 'F'):
                                visible_len += 2
                            else:
                                visible_len += 1
                        
                        padding = " " * max(0, wrap_width - visible_len)
                        middle += f"│ {colored_line}{padding} │\n"
                        
                    if not show_full_preview and total_lines > 5:
                        frmt_str = f" ... ({total_lines-5} more lines) "
                        middle += f"│ {self.fix_color}{frmt_str.ljust(wrap_width, ' ')}{RESET_COLOR} │\n"
                else:
                    middle += f"│ {(' No Content ').ljust(safe_width -4, ' ') } │\n"
                    
                middle += f"├{'':─^{safe_width-2}}┤\n"
                middle += f"│ {('Grant Permission ?').ljust(safe_width -4, ' ') } │\n"
                middle += f"│{' '*(safe_width-2)}│\n"
                
                print(top, end="")
                print(middle, end="")
                
                if action_name == 'CREATE':
                    options = ['Yes, create this file', 'Always allow file creations in ./src/', 'No, cancel operation']
                else:
                    options = ['Yes, append to this file', 'No, cancel operation']
                    
                if not show_full_preview and total_lines > 5:
                    options.insert(1, 'Preview entire file')
                    
                selected = self.display_options(options, safe_width)
                
                if selected == 'Preview entire file':
                    show_full_preview = True
                    print()
                    continue
                else:
                    return selected

            elif action_name == 'DELETE':
                middle += f"│ {('Grant Permission ?').ljust(safe_width -4, ' ') } │\n"
                middle += f"│{' '*(safe_width-2)}│\n"
                print(top, end="")
                print(middle, end="")
                options = ['Yes, delete this file', 'No, cancel operation']
                return self.display_options(options, safe_width)
                
            elif action_name == 'EDIT':
                if show_full_preview:
                    surrounding = 999999
                    title = " FULL PREVIEW "
                else:
                    surrounding = 3
                    title = " DIFF "
                
                middle += f"├{title:─^{safe_width-2}}┤\n"
                
                _, diff_lines = self.compare_editing(
                    file_path, content, language, 
                    surrounding_lines=surrounding, 
                    embed_width=safe_width
                )
                
                for d_line in diff_lines:
                    middle += d_line + "\n"
                
                middle += f"├{'':─^{safe_width-2}}┤\n"
                middle += f"│ {('Grant Permission ?').ljust(safe_width -4, ' ') } │\n"
                middle += f"│{' '*(safe_width-2)}│\n"
                
                print(top, end="")
                print(middle, end="")
                
                options = ['Yes, apply these edits', 'Preview entire file', 'No, cancel operation']
                
                if show_full_preview:
                    options.remove('Preview entire file')
                    
                selected = self.display_options(options, safe_width)
                
                if selected == 'Preview entire file':
                    show_full_preview = True
                    print()
                    continue
                else:
                    return selected

    def print_highlighted_code(self, code_string: str, file_path: str, language_name: str, inside_box: bool = False, width: int = None):
        """
        Applies Pygments formatting rules to code segments.

        Args:
            code_string (str): Target script/code block.
            file_path (str): Correlated file path identifier.
            language_name (str): Syntax formatting language target.
            inside_box (bool, optional): Formatting mode. Defaults to False.
            width (int, optional): Strict terminal width boundaries. Defaults to None.

        Returns:
            list[str] | str: Highlighted data structure depending on configuration state.
        """
        if width is None:
            width = getattr(self, 'printable_width', 80)
            
        code_string = code_string.expandtabs(4)
        code_lines = code_string.splitlines()
        wrapped_raw_lines = []
        
        wrap_width = max(10, width - (4 if inside_box else 0))
        
        for text in code_lines:
            text = text.rstrip() 
            if not text:
                wrapped_raw_lines.append("")
            else:
                wrapped_lines = textwrap.wrap(
                    text, 
                    width=wrap_width, 
                    drop_whitespace=False,
                    replace_whitespace=False
                )
                wrapped_raw_lines.extend(wrapped_lines)
                
        wrapped_code_string = "\n".join(wrapped_raw_lines)

        try:
            lexer = get_lexer_by_name(language_name.strip().lower())
        except ClassNotFound:
            try:
                lexer = guess_lexer(wrapped_code_string)
            except ClassNotFound:
                lexer = get_lexer_by_name("text")
                
        formatter = Terminal256Formatter(style="monokai")
        colored_output = highlight(wrapped_code_string, lexer, formatter)
        colored_lines = colored_output.splitlines()
        
        while len(colored_lines) < len(wrapped_raw_lines):
            colored_lines.append("")

        if inside_box:
            title = f" [ {file_path} - {language_name} ] " if file_path else " [ Code ] "
            top = f"{self.fix_color}╭{title:─^{wrap_width + 2}}╮{RESET_COLOR}\n"
            middle = ""
            for colored_line in colored_lines:
                visible_text = ANSI_ESCAPE.sub('', colored_line)
                visible_len = 0
                for char in visible_text:
                    if unicodedata.east_asian_width(char) in ('W', 'F'):
                        visible_len += 2
                    else:
                        visible_len += 1
                
                padding_spaces = " " * max(0, wrap_width - visible_len)
                middle += f"{self.fix_color}│ {RESET_COLOR}{colored_line}{padding_spaces} {self.fix_color}│{RESET_COLOR}\n"
                
            return top + middle
        else:
            return colored_lines

    def display_options(self, options: list, width: int) -> str:
        """
        Manages the terminal interface to process interactive user key inputs.

        Args:
            options (list): Sequential block of selection options.
            width (int): Display boundary width.

        Returns:
            str: Resolved user selection mapped to the options block.
        """
        if os.name == 'nt': 
            import msvcrt
            def get_key() -> str:
                """
                Extracts raw terminal keystroke sequences using native Windows APIs.

                Args:
                    None

                Returns:
                    str: Standardized control instruction mapped to the OS payload.
                """
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'): 
                    ch = msvcrt.getch()
                    if ch == b'H': return 'up'
                    if ch == b'P': return 'down'
                elif ch in (b'\r', b'\n'):
                    return 'enter'
                elif ch == b'\x03': 
                    raise KeyboardInterrupt
                return None
        else:
            import tty
            import termios
            import select
            def get_key() -> str:
                """
                Extracts raw terminal keystroke sequences via Unix tty environments.

                Args:
                    None

                Returns:
                    str: Standardized control instruction derived from stdin buffer sequences.
                """
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setraw(fd)
                    ch = sys.stdin.read(1)
                    if ch == '\x1b': 
                        if select.select([sys.stdin], [], [], 0.01)[0]:
                            seq = sys.stdin.read(2)
                            if seq == '[A': return 'up'
                            if seq == '[B': return 'down'
                        return 'esc'
                    elif ch in ('\r', '\n'):
                        return 'enter'
                    elif ch == '\x03':
                        raise KeyboardInterrupt
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                return None

        def select_element(options: list, width: int) -> str:
            """
            Synchronizes terminal cursor placements for dynamic option menus.

            Args:
                options (list): Collection of user-selectable paths.
                width (int): Current operating column limit constraints.

            Returns:
                str: Selected menu output resolved by manual user interaction.
            """
            if not options:
                raise ValueError("Options list cannot be empty.")

            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

            selected = 0
            num_options = len(options)
            total_lines = num_options + 1

            sys.stdout.write("\n" * total_lines)
            
            try:
                while True:
                    sys.stdout.write(f"\033[{total_lines}A")
                    
                    for i, opt in enumerate(options):
                        if i == selected:
                            formatted_opt = f"> {opt}"[:width].ljust(width-4, " ")
                            sys.stdout.write(f"│ \033[K\033[7m{formatted_opt}\033[0m │\r\n")
                        else:
                            formatted_opt = f"  {opt}"[:width].ljust(width-4, " ")
                            sys.stdout.write(f"│ \033[K{formatted_opt} │\r\n")
                    sys.stdout.write(f"\033[K╰{'─' * (width - 2)}╯\r\n")
                    sys.stdout.flush()

                    key = get_key()

                    if key == 'up':
                        selected = max(0, selected - 1)
                    elif key == 'down':
                        selected = min(num_options - 1, selected + 1)
                    elif key == 'enter':
                        break
                        
            finally:
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()

            return options[selected]
        
        return select_element(options, width)

    def new_line(self):
        """
        Outputs a standard trailing newline sequence to standard output.

        Args:
            None

        Returns:
            None
        """
        print()

    def line_break(self):
        """
        Renders a fixed horizontal terminal divider element.

        Args:
            None

        Returns:
            None
        """
        print("─" * self.width)