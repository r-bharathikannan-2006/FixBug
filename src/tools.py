import os
import re
from general import folder_validation
import difflib

class AIActionExecutor:
    """Executes parsed file operations and modifications from text payloads."""
    
    def __init__(self, display_instance, get_cwd_func):
        """Initializes the AIActionExecutor with display and path dependencies.

        Args:
            display_instance (object): Instance handling UI display and user prompts.
            get_cwd_func (callable): Function returning the current working directory string.

        Returns:
            None
        """
        self.action_pattern = re.compile(
            r"<<<\s*ACTION:\s*(?P<action>[A-Z]+)\s*\|\s*FILE:\s*(?P<file>[^\s>]+)\s*\|\s*LANGUAGE:\s*(?P<language>[a-zA-Z]+)\s*>>>\n?"
            r"(?P<content>.*?)\n?"
            r"<<<\s*END ACTION\s*>>>",
            re.DOTALL | re.IGNORECASE
        )
        
        self.search_replace_pattern = re.compile(
            r"<<<\s*SEARCH\s*>>>\n?(.*?)\n?<<<\s*REPLACE\s*>>>\n?(.*?)(?=(?:<<<\s*SEARCH\s*>>>|$))",
            re.DOTALL
        )

        self.display = display_instance
        self.get_cwd = get_cwd_func

    def execute_from_text(self, ai_response_text: str):
        """Parses payload text and executes valid action blocks.

        Args:
            ai_response_text (str): The raw text payload containing action definitions.

        Returns:
            None
        """
        matches = list(self.action_pattern.finditer(ai_response_text))
        
        # Compute total actionable modifications for progress tracking
        total_actions = len([m for m in matches if m.group('action').upper() not in ['EXPLAIN', 'FIX', 'READ']])
        action_count = 0

        for match in matches:
            action = match.group('action').upper()
            filepath = match.group('file')
            language = match.group('language')
            
            if filepath.upper() == "NULL":
                filepath = None
                
            content = match.group('content').strip()

            if action in ["EXPLAIN", "FIX", "READ"]:
                # Bypass progress increment for read-only operations
                self._route_action(action, filepath, content, language, 0, total_actions)
            else:
                action_count += 1
                self._route_action(action, filepath, content, language, action_count, total_actions)

        if total_actions == 0:
            self.display.display_progress("No file modification blocks found in the AI response.")

    def _route_action(self, action: str, filepath: str, content: str, language: str, action_number: int, total_actions: int):
        """Routes parsed data payload to the corresponding file operation handler.

        Args:
            action (str): The explicit operation type to execute.
            filepath (str): The target file path for the operation.
            content (str): The data payload to write, append, or replace.
            language (str): The programming language associated with the payload.
            action_number (int): The current index of the actionable operation.
            total_actions (int): The aggregate count of actionable operations.

        Returns:
            None
        """
        if action == "EXPLAIN":
            self.display.display_explanation(content)
        elif action == "FIX":
            self.display.display_fixes(content)
        elif action == "READ":
            # Read operations are handled upstream in the event loop
            pass 
            
        elif action == "CREATE":
            choice = self.display.display_action_info(
                action_number, "CREATE", filepath, content,
                "AI is creating a new file.", language, total_actions, self.get_cwd()
            )
            if choice and (choice.startswith('Yes') or choice.startswith('Always allow')):
                self._handle_create(filepath, content)

        elif action == "APPEND":
            choice = self.display.display_action_info(
                action_number, "APPEND", filepath, content,
                "AI is appending text to the end of the file.", language, total_actions, self.get_cwd()
            )
            if choice and choice.startswith('Yes'):
                self._handle_append(filepath, content)

        elif action == "DELETE":
            choice = self.display.display_action_info(
                action_number, "DELETE", filepath, "",
                "AI requested to delete this file.", "text", total_actions, self.get_cwd(),
                del_details="Ready to delete"
            )
            if choice and choice.startswith('Yes'):
                self._handle_delete(filepath)

        elif action == "EDIT":
            choice = self.display.display_action_info(
                action_number, "EDIT", filepath, content,
                "AI requested modifications to the existing code.", language, total_actions, self.get_cwd()
            )
            if choice and choice.startswith('Yes'):
                self._handle_edit(filepath, content)
        else:
            self.display.display_progress(f"[!] Unknown action type: {action}")

    def _handle_create(self, filepath: str, content: str):
        """Initializes a new file with the provided payload.

        Args:
            filepath (str): The target destination path for the new file.
            content (str): The string payload to write.

        Returns:
            None
        """
        if not filepath: return

        # Validate path against directory traversal violations
        if not folder_validation(filepath, self.get_cwd()):
            self.display.display_progress(f"[!] Security Block: AI attempted to modify an out-of-bounds file: {filepath}")
            return
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    def _handle_append(self, filepath: str, content: str):
        """Appends payload to target file stream.

        Args:
            filepath (str): The target file path to append data to.
            content (str): The string payload to append.

        Returns:
            None
        """
        if not filepath: return

        # Validate path against directory traversal violations
        if not folder_validation(filepath, self.get_cwd()):
            self.display.display_progress(f"[!] Security Block: AI attempted to modify an out-of-bounds file: {filepath}")
            return
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                f.write("\n")
            f.write(content)

    def _handle_delete(self, filepath: str):
        """Removes target file from the filesystem.

        Args:
            filepath (str): The target path of the file to be removed.

        Returns:
            None
        """
        if not filepath: return

        # Validate path against directory traversal violations
        if not folder_validation(filepath, self.get_cwd()):
            self.display.display_progress(f"[!] Security Block: AI attempted to modify an out-of-bounds file: {filepath}")
            return
        if os.path.exists(filepath):
            os.remove(filepath)

    def _handle_edit(self, filepath: str, content: str):
        """Processes structural replacements within an existing file.

        Args:
            filepath (str): The target file path to apply modifications.
            content (str): The payload containing search and replace blocks.

        Returns:
            None
        """
        target_path = os.path.join(self.get_cwd(), filepath)
        
        if not target_path or not os.path.exists(target_path):
            return
            
        # Validate path against directory traversal violations
        if not folder_validation(filepath, self.get_cwd()):
            self.display.display_progress(f"[!] Security Block: AI attempted to modify an out-of-bounds file: {filepath}")
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            file_data = f.read()
            
        replacements = self.search_replace_pattern.findall(content)
        
        for search_text, replace_text in replacements:
            search_text_norm = search_text.rstrip('\r\n')
            replace_text_norm = replace_text.rstrip('\r\n')
            
            # Execute fast exact match
            if search_text_norm in file_data:
                file_data = file_data.replace(search_text_norm, replace_text_norm, 1)
                continue
                
            # Execute fallback fuzzy match via sequence matching
            file_lines = file_data.splitlines()
            search_lines = search_text_norm.splitlines()
            
            if not search_lines:
                continue
                
            # Normalize whitespace to mitigate formatting discrepancies
            stripped_file = [line.strip() for line in file_lines]
            stripped_search = [line.strip() for line in search_lines]
            
            matcher = difflib.SequenceMatcher(None, stripped_file, stripped_search)
            match = matcher.find_longest_match(0, len(stripped_file), 0, len(stripped_search))
            
            # Verify contiguous sequence match meets the minimum confidence threshold
            if match.size > 0 and (match.size / max(1, len(search_lines))) >= 0.6:
                start_idx = match.a
                
                # Isolate target lines for replacement
                end_idx = min(len(file_lines), match.a + len(search_lines)) 
                
                # Splice replacement payload into file content
                new_file_lines = file_lines[:start_idx] + replace_text_norm.splitlines() + file_lines[end_idx:]
                
                # Serialize with standard line terminators
                file_data = "\n".join(new_file_lines) + "\n"
            else:
                self.display.display_progress(f"[!] Warning: Could not securely locate the SEARCH block in {filepath}. Skipping this specific edit.")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(file_data)