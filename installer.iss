name: Build and Release FixBug

on:
  workflow_dispatch:
    inputs:
      tag_name:
        description: 'Release Tag Version (e.g. v1.0.0)'
        required: true
        default: 'v1.0.0'
  push:
    tags:
      - 'v*' # Trigger the workflow on version tags

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: windows-latest
    strategy:
      max-parallel: 1 # Prevents GitHub release creation race conditions
      matrix:
        architecture: ['x64', 'x86']
    
    env:
      BUILD_ARCH: ${{ matrix.architecture }} # Pass the arch down to Inno Setup

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          architecture: ${{ matrix.architecture }} # Forces 32-bit Python for x86

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -r requirements.txt

      - name: Build executable with PyInstaller
        run: |
          pyinstaller --name fbcore --icon=assets/fixbug.ico --collect-data cfonts --hidden-import tree_sitter_python --hidden-import tree_sitter_javascript --hidden-import tree_sitter_typescript --hidden-import tree_sitter_java --hidden-import tree_sitter_kotlin --hidden-import tree_sitter_c_sharp --hidden-import tree_sitter_c --hidden-import tree_sitter_cpp --hidden-import tree_sitter_go --hidden-import tree_sitter_rust --hidden-import tree_sitter_php --hidden-import tree_sitter_swift --hidden-import tree_sitter_ruby --hidden-import tree_sitter_bash --hidden-import tree_sitter_powershell --hidden-import tree_sitter_sql --hidden-import tree_sitter_dart src/main.py

      - name: Compile Inno Setup Installer
        uses: Minionguyjpro/Inno-Setup-Action@v1.2.2
        with:
          path: app_installer.iss

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ inputs.tag_name || github.ref_name }}
          files: Output/FixBug_core_Installer_${{ matrix.architecture }}.exe
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
