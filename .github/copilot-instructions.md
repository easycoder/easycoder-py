# EasyCoder-py AI Assistant Instructions

This guide helps AI coding assistants understand and work effectively with the EasyCoder-py codebase.

## Project Overview

EasyCoder-py is a high-level English-like domain-specific scripting language (DSL) implemented in Python. Key characteristics:

- English-like syntax focused on vocabulary rather than structure
- Command-line based with an emerging graphics module using PySide6
- Acts as a wrapper around standard Python functions
- Extensible through plugin modules
- Suitable for prototyping, rapid testing, and control systems

## Core Architecture

### Main Components:

1. Core Language (`easycoder/`)
   - `ec_compiler.py`: Handles script compilation
   - `ec_program.py`: Manages program execution
   - `ec_core.py`: Core language features
   - `ec_value.py`: Value handling
   - `ec_condition.py`: Condition processing

2. Plugin System (`plugins/`)
   - Seamlessly extends language functionality
   - Example: `points.py` demonstrates coordinate handling

3. Documentation (`doc/`)
   - Core features in `doc/core/`
   - Graphics features in `doc/graphics/`
   - Each keyword/value/condition documented separately

## Development Workflows

### Testing

1. Run the comprehensive test suite:
```bash
easycoder scripts/tests.ecs
```

2. Performance benchmarking:
```bash
easycoder scripts/benchmark.ecs
```

### Script Development

1. Basic script structure:
```
script ScriptName
    ! Your code here
    exit
```

2. Debugging:
- Use `log` instead of `print` for timestamped debug output
- Example: `log 'Debug message'` outputs with timestamp and line number

## Project Conventions

1. Script Files
- Extension: `.ecs`
- Always include `exit` command to properly terminate
- Use `script Name` to identify scripts for debugging

2. Plugin Development
- Place new plugins in `plugins/` directory
- Must provide both compiler and runtime modules
- See `plugins/points.py` for reference implementation

3. Documentation
- Place in `doc/` with appropriate subdirectory
- One markdown file per language feature
- Include syntax, parameters, and examples

## Common Patterns

1. Error Handling
```
on error
    log error
    exit
```

2. Variable Declaration
```
variable Name
set Name to Value
```

3. Plugin Integration
```
use plugin-name
! Plugin-specific commands
```

## Key Integration Points

1. Python Integration
- EasyCoder wraps Python functionality
- Custom plugins can wrap any Python library with suitable API
- Direct Python integration via `system` command

2. Graphics (PySide6)
- Graphics module under active development
- See `doc/graphics/` for current features
- Uses plugin system for seamless integration

Remember: Focus on English-like syntax and readability when writing or modifying code. Keep scripts as readable as natural language where possible.