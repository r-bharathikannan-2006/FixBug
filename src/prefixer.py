from pathlib import Path
import sys
import importlib
from tree_sitter import Language, Parser

class Prefixer:
    """Analyzes directory structures and generates abstract syntax tree representations.

    Provides utilities to traverse directory trees while ignoring specified
    environments and generates XML-formatted AST structures for supported source files.
    """

    IGNORE_DIRS = {
        "venv",
        ".venv",
        "env",
        ".env",
        "node_modules",
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        "vendor",  
    }

    def __init__(self, directory: str):
        """Initializes the Prefixer with a target directory and language mappings.

        Args:
            directory (str): The root directory path to process.
        """
        self.directory = Path(directory)

        self.parser = Parser()
        self.language_map = {}
        
        lang_configs = {
            '.py': ('tree_sitter_python', 'language'),
            '.pyw': ('tree_sitter_python', 'language'),
            '.js': ('tree_sitter_javascript', 'language'),
            '.jsx': ('tree_sitter_javascript', 'language'),
            '.mjs': ('tree_sitter_javascript', 'language'),
            '.cjs': ('tree_sitter_javascript', 'language'),
            '.ts': ('tree_sitter_typescript', 'language_typescript'),
            '.tsx': ('tree_sitter_typescript', 'language_tsx'),
            '.java': ('tree_sitter_java', 'language'),
            '.kt': ('tree_sitter_kotlin', 'language'),
            '.kts': ('tree_sitter_kotlin', 'language'),
            '.cs': ('tree_sitter_c_sharp', 'language'),
            '.c': ('tree_sitter_c', 'language'),
            '.h': ('tree_sitter_c', 'language'),
            '.cpp': ('tree_sitter_cpp', 'language'),
            '.hpp': ('tree_sitter_cpp', 'language'),
            '.cc': ('tree_sitter_cpp', 'language'),
            '.go': ('tree_sitter_go', 'language'),
            '.rs': ('tree_sitter_rust', 'language'),
            '.php': ('tree_sitter_php', 'language_php'),
            '.swift': ('tree_sitter_swift', 'language'),
            '.rb': ('tree_sitter_ruby', 'language'),
            '.sh': ('tree_sitter_bash', 'language'),
            '.bash': ('tree_sitter_bash', 'language'),
            '.zsh': ('tree_sitter_bash', 'language'),
            '.ps1': ('tree_sitter_powershell', 'language'),
            '.sql': ('tree_sitter_sql', 'language'),
            '.dart': ('tree_sitter_dart', 'language'),
        }

        # Load available language bindings from installed packages
        for ext, (mod_name, func_name) in lang_configs.items():
            try:
                mod = importlib.import_module(mod_name)
                self.language_map[ext] = Language(getattr(mod, func_name)())
            except (ImportError, AttributeError):
                pass

        self.structure_types = {
            'function_definition', 'function_declaration', 'arrow_function',
            'method_definition', 'method_declaration',
            'class_definition', 'class_declaration', 'class_specifier',
            'function_item', 'struct_item', 'impl_item',
            'type_declaration',
            'class', 'method', 'singleton_method', 'module',
            'interface_declaration', 'struct_specifier', 'enum_declaration',
            'create_function_statement', 'create_procedure_statement'
        }

        self.identifier_types = {
            'identifier', 'name', 'property_identifier', 
            'type_identifier', 'field_identifier', 
            'variable_name', 'constant'
        }

    def directory_tree(self):
        """Generates a visual tree representation of the directory structure.

        Returns:
            str: The formatted directory tree.
        """
        def is_virtualenv(dir_path: Path) -> bool:
            """Evaluates whether a given directory path is a Python virtual environment.

            Args:
                dir_path (Path): The directory path to evaluate.

            Returns:
                bool: True if the directory is a virtual environment, False otherwise.
            """
            if not dir_path.is_dir():
                return False
    
            # Check for modern virtual environment configuration
            if (dir_path / "pyvenv.cfg").exists():
                return True
    
            # Verify binaries directory structure for legacy or conda environments
            has_bin = (dir_path / "bin" / "python").exists() or (
                dir_path / "bin" / "python.exe"
            ).exists()
            has_scripts = (dir_path / "Scripts" / "python.exe").exists()
    
            return has_bin or has_scripts

        def _recur_dir_tree(dir_path: Path, prefix: str = ""):
            """Traverses the directory recursively to build the tree string.

            Args:
                dir_path (Path): The current directory being traversed.
                prefix (str, optional): The string prefix for the current tree depth.

            Returns:
                str: The string representation of the current directory branch.
            """
            if not dir_path.is_dir():
                return ""
            contents = []
            for path in dir_path.iterdir():
                # Exclude predefined ignored directories
                if path.name in self.IGNORE_DIRS:
                    continue
    
                # Exclude dynamically detected virtual environments
                if path.is_dir() and is_virtualenv(path):
                    continue
    
                contents.append(path)
            
            contents = sorted(contents, key=lambda p: (not p.is_dir(), p.name.lower()))
    
            tree_str = ""
    
            for index, path in enumerate(contents):
                # Calculate branch connector symbol
                is_last = index == len(contents) - 1
                connector = "└── " if is_last else "├── "
    
                tree_str += f"{prefix}{connector}{path.name}\n"
    
                if path.is_dir():
                    extension = "    " if is_last else "│   "
                    tree_str += _recur_dir_tree(path, prefix + extension)
    
            return tree_str
        
        return _recur_dir_tree(dir_path=self.directory)

    def abstract_syntax_tree(self, filepath: str) -> str:
        """Parses a source file and returns its abstract syntax tree formatted as XML.

        Args:
            filepath (str): The path to the source file.

        Returns:
            str: The XML representation of the file's abstract syntax tree.

        Raises:
            ValueError: If the file extension is not supported or missing bindings.
        """
        def _get_structure_name(node, source_bytes: bytes) -> str:
            name_node = node.child_by_field_name('name')
            if name_node:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode('utf8')

            if node.type in ('function_definition', 'function_declaration'):
                decl_node = node.child_by_field_name('declarator')
                if decl_node:
                    def find_ident(n):
                        if n.type in ('identifier', 'field_identifier', 'name'):
                            return n
                        for c in n.children:
                            res = find_ident(c)
                            if res: return res
                        return None
                    
                    ident_node = find_ident(decl_node)
                    if ident_node:
                        return source_bytes[ident_node.start_byte:ident_node.end_byte].decode('utf8')

            if node.type == 'arrow_function':
                parent = node.parent
                if parent:
                    if parent.type == 'variable_declarator':
                        name_node = parent.child_by_field_name('name')
                        if name_node:
                            return source_bytes[name_node.start_byte:name_node.end_byte].decode('utf8')
                    elif parent.type == 'pair':
                        key_node = parent.child_by_field_name('key')
                        if key_node:
                            return source_bytes[key_node.start_byte:key_node.end_byte].decode('utf8')
                return "<anonymous>"

            for child in node.children:
                if child.type in ('identifier', 'type_identifier', 'name', 'variable_name', 'constant'):
                    return source_bytes[child.start_byte:child.end_byte].decode('utf8')

            return "unknown_structure"

        def _parse_scope(node, structure_name, source_bytes):
            """Recursively parses a syntax node to extract variables and nested structures.

            Args:
                node: The current tree-sitter node being evaluated.
                structure_name (str): The identifier of the current structure.
                source_bytes (bytes): The source code as a byte sequence.

            Returns:
                tuple: A set of extracted variables and a list of nested child structures.
            """
            variables = set()
            nested_structures = []

            def walk(n):
                if n.type in self.structure_types:
                    struct_name = _get_structure_name(n, source_bytes)
                    is_class = any(kw in n.type for kw in ['class', 'struct', 'impl', 'interface', 'module'])
                    node_type = "Class/Struct" if is_class else "Function/Method"
                    
                    # Extract sub-scope prior to continuing traversal
                    child_vars, child_structs = _parse_scope(n, struct_name, source_bytes)
                    
                    nested_structures.append({
                        'type': node_type,
                        'name': struct_name,
                        'start_line': n.start_point[0] + 1,
                        'end_line': n.end_point[0] + 1,
                        'variables': child_vars,
                        'children': child_structs
                    })
                    return  # Halt walking; branch handled by recursive call
                
                if n.type in self.identifier_types:
                    var_name = source_bytes[n.start_byte:n.end_byte].decode('utf8')
                    if var_name != structure_name:
                        variables.add(var_name)
                        
                for c in n.children:
                    walk(c)

            for c in node.children:
                walk(c)
                
            # Sort nested structures chronologically by start line
            nested_structures.sort(key=lambda x: x['start_line'])
            return variables, nested_structures

        def _escape_xml(text: str) -> str:
            """Escapes reserved XML characters in a given string.

            Args:
                text (str): The raw string to escape.

            Returns:
                str: The XML-safe string.
            """
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        def _format_xml_node(struct, depth=1) -> list[str]:
            lines = []
            indent = "  " * depth
            child_indent = "  " * (depth + 1)
            
            tag_name = "class" if struct['type'] == "Class/Struct" else "function"
            name = _escape_xml(struct['name'])
            
            lines.append(f'{indent}<{tag_name} name="{name}" lines="{struct["start_line"]}-{struct["end_line"]}">')
            
            if struct['variables']:
                for var in sorted(list(struct['variables'])):
                    # Apply XML escaping to variable name attribute
                    lines.append(f'{child_indent}<variable name="{_escape_xml(var)}" />')
                
            if struct['children']:
                for child in struct['children']:
                    lines.append("")  # Insert vertical spacing for nested structures
                    lines.extend(_format_xml_node(child, depth + 1))
                    
            lines.append(f'{indent}</{tag_name}>')
            return lines

        def _format_xml(global_vars, root_structures) -> str:
            lines = ["<file_metadata>"]
            
            if global_vars:
                var_str = _escape_xml(", ".join(sorted(list(global_vars))))
                lines.append("<global_variables>")
                lines.append(var_str)
                lines.append("</global_variables>\n")
                
            if root_structures:
                lines.append("<functions>")
                for i, struct in enumerate(root_structures):
                    lines.extend(_format_xml_node(struct, depth=1))
                    if i < len(root_structures) - 1:
                        lines.append("")  # Insert vertical spacing between top-level declarations
                lines.append("</functions>")
                
            lines.append("</file_metadata>")
            return "\n".join(lines)

        ext = Path(filepath).suffix.lower()
        if ext not in self.language_map:
            raise ValueError(f"Unsupported or missing tree-sitter package for extension: {ext}")

        self.parser.language = self.language_map[ext]

        with open(filepath, 'rb') as f:
            source_bytes = f.read()

        tree = self.parser.parse(source_bytes)
        
        # Parse logical hierarchy from the root scope
        global_vars, root_structures = _parse_scope(tree.root_node, None, source_bytes)
        
        # Format extracted hierarchy into XML
        return _format_xml(global_vars, root_structures)