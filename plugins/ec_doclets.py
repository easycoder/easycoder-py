#!/usr/bin/env python3
"""
Doclet Search - Use a local LLM to search through dated note files
"""
import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Union
import requests

class DocletManager:
    def __init__(self, doclets_dir: str = None, ollama_url: str = "http://localhost:11434"):
        """Initialize the doclet manager
        
        Args:
            doclets_dir: Root directory or comma-separated list of directories containing year folders
            ollama_url: URL of the local Ollama API
        """
        # Support comma-separated list of directories
        if doclets_dir:
            paths = [p.strip() for p in doclets_dir.split(',')]
            self.doclets_dirs = [Path(p) for p in paths]
        else:
            self.doclets_dirs = [Path(__file__).parent]
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # Default model, can be changed
        
    def find_all_doclets(self) -> List[Tuple[Path, str, str]]:
        """Find all doclets in the directory structure
        
        Returns:
            List of tuples: (filepath, filename, subject_line)
        """
        doclets = []
        
        # Search across all configured directories
        for base_dir in self.doclets_dirs:
            # Look for year folders (e.g., 2026, 2025, etc.)
            for year_folder in base_dir.glob("[0-9][0-9][0-9][0-9]"):
                if year_folder.is_dir():
                    # Find all .md files in this year folder
                    for doclet_file in year_folder.glob("*.md"):
                        # Read the subject line (first line starting with '# ')
                        try:
                            with open(doclet_file, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                subject = first_line[2:].strip() if first_line.startswith('# ') else "No subject"
                                doclets.append((doclet_file, doclet_file.name, subject))
                        except Exception as e:
                            print(f"Warning: Could not read {doclet_file}: {e}", file=sys.stderr)
        
        return sorted(doclets, key=lambda x: x[1])

    def _get_base_dir_label(self, filepath: Path) -> str:
        """Return the name of the top-level doclets directory for this file."""
        for base_dir in self.doclets_dirs:
            try:
                filepath.relative_to(base_dir)
                return base_dir.name or str(base_dir)
            except ValueError:
                continue
        return ""

    def get_doclet_by_filename(self, name: str) -> Optional[Tuple[Path, str, str]]:
        """Find a single doclet by filename (accepts with/without .md).

        Accepts first-token matching: pass in the leading part of the query
        and we'll normalize to YYMMDD-NN.md.
        """
        token = name.strip()
        # Trim common trailing punctuation from token
        token = token.rstrip(',:;.!')
        # Normalize to filename with .md
        if token.endswith('.md'):
            fname = token
        else:
            fname = f"{token}.md"

        for filepath, filename, subject in self.find_all_doclets():
            if filename == fname:
                return (filepath, filename, subject)
        return None
    
    def read_doclet_content(self, filepath: Path) -> str:
        """Read the full content of a doclet file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    def build_search_context(self, doclets: List[Tuple[Path, str, str]]) -> str:
        """Build a context string for the LLM with all doclet metadata
        
        Args:
            doclets: List of (filepath, filename, subject) tuples
            
        Returns:
            Formatted string with doclet information
        """
        context_parts = ["Available doclets:\n"]
        for filepath, filename, subject in doclets:
            context_parts.append(f"- {filename}: {subject}")
        
        return "\n".join(context_parts)
    
    def query_llm(self, prompt: str, model: str = None) -> str:
        """Query the local Ollama LLM
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model name (defaults to self.model)
            
        Returns:
            Response text from the LLM
        """
        if model is None:
            model = self.model
            
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get('response', '').strip()
        except requests.exceptions.RequestException as e:
            return f"Error querying LLM: {e}"
    
    def _match_doclets(self, query: str, use_llm: bool = False) -> Tuple[List[Tuple[Path, str, str]], Optional[str], Dict[str, Any]]:
        """Return matching doclets, optional error code, and metadata."""
        doclets = self.find_all_doclets()
        meta: Dict[str, Any] = {
            "doclet_count": len(doclets),
            "use_llm": use_llm,
            "match_count": 0,
            "matched_by": None,
            "status": None,
        }

        if not doclets:
            meta["status"] = "no_doclets"
            return [], "no_doclets", meta

        query_lower = query.lower().strip()
        if not query_lower:
            meta["status"] = "empty_query"
            return [], "empty_query", meta

        # Deterministic subject+body substring match
        deterministic_matches = []
        for filepath, fname, subject in doclets:
            subj_lower = subject.lower()
            body_lower = self.read_doclet_content(filepath).lower()
            haystack = subj_lower + "\n" + body_lower
            if query_lower in haystack:
                deterministic_matches.append((filepath, fname, subject))

        llm_matches = []
        if use_llm:
            entries = []
            for filepath, fname, subject in doclets:
                body = self.read_doclet_content(filepath)
                preview = body[:400].replace('\n', ' ')
                entries.append(f"- {fname} | subject: {subject} | preview: {preview}")

            context = "\n".join(entries)
            prompt = f"""You are a precise doclet search helper.
Doclets are listed below as: filename | subject | preview
User query: {query}

Select the filenames that are relevant to the query (semantic matches OK, handle typos).
Return ONLY filenames, one per line. If none, respond with NO_MATCHES.

Doclets:\n{context}
"""

            llm_response = self.query_llm(prompt)
            if "NO_MATCHES" not in llm_response:
                for line in llm_response.strip().split('\n'):
                    line = line.strip()
                    if line.endswith('.md'):
                        fname = line
                    elif re.match(r'^\d{6}-\d{2}$', line):
                        fname = f"{line}.md"
                    else:
                        continue
                    for fp, f, subj in doclets:
                        if f == fname:
                            llm_matches.append((fp, f, subj))
                            break

        matching_files = llm_matches if use_llm and llm_matches else deterministic_matches

        meta["match_count"] = len(matching_files)
        meta["matched_by"] = "llm" if use_llm and llm_matches else "deterministic"

        if not matching_files:
            meta["status"] = "no_matches"
            return [], "no_matches", meta

        meta["status"] = "ok"
        return matching_files, None, meta

    def search_data(self, query: str, include_content: bool = False, use_llm: bool = False, include_summary: bool = False, return_meta: bool = False) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
        """Programmatic search returning raw data; optionally include metadata."""
        matches, error, meta = self._match_doclets(query=query, use_llm=use_llm)

        results: List[Dict[str, Any]] = []
        if not error:
            for filepath, filename, subject in matches:
                entry: Dict[str, Any] = {
                    "filepath": filepath,
                    "filename": filename,
                    "display_filename": f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename,
                    "subject": subject,
                }

                content: Optional[str] = None
                if include_content or include_summary:
                    content = self.read_doclet_content(filepath)

                if include_content and content is not None:
                    entry["content"] = content

                if include_summary and content is not None:
                    snippet_raw = content.strip().replace('\n', ' ')
                    entry["summary"] = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw

                results.append(entry)

        if return_meta:
            meta["results_included"] = bool(results)
            return results, meta

        return results

    def search(self, query: str, include_content: bool = False, use_llm: bool = False, include_summary: bool = False) -> str:
        """Search doclets using deterministic matching, optional LLM rerank/semantic."""
        # Fast-path: when listing contents, allow direct filename access
        if include_content:
            first_token = re.split(r"\s+", query.strip(), maxsplit=1)[0] if query.strip() else ""
            # Match YYMMDD-NN optionally with .md
            if re.match(r"^\d{6}-\d{2}(\.md)?$", first_token):
                record = self.get_doclet_by_filename(first_token)
                if record:
                    filepath, filename, subject = record
                    display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
                    content = self.read_doclet_content(filepath)
                    snippet = None
                    if include_summary:
                        snippet_raw = content.strip().replace('\n', ' ')
                        snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                    block_lines = [f"{'='*70}", f"File: {display_name}", f"Subject: {subject}"]
                    if snippet:
                        block_lines.append(f"Summary: {snippet}")
                    block_lines.append(f"{'='*70}")
                    block_lines.append(content)
                    block_lines.append(f"{'='*70}")
                    return "\n".join(block_lines)

        matches, error, _meta = self._match_doclets(query=query, use_llm=use_llm)

        if error == "no_doclets":
            return "No doclets found in the directory structure."
        if error == "empty_query":
            return "Please provide a search query."
        if error == "no_matches":
            return "No matching doclets found for your query."

        result_parts = [f"Found {len(matches)} matching doclet{'s' if len(matches) != 1 else ''}:\n"]
        for filepath, filename, subject in matches:
            display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
            if include_content:
                content = self.read_doclet_content(filepath)
                snippet = None
                if include_summary:
                    snippet_raw = content.strip().replace('\n', ' ')
                    snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                block_lines = [f"{'='*70}", f"File: {display_name}", f"Subject: {subject}"]
                if snippet:
                    block_lines.append(f"Summary: {snippet}")
                block_lines.append(f"{'='*70}")
                block_lines.append(content)
                block_lines.append(f"{'='*70}")
                result_parts.append("\n".join(block_lines))
            else:
                if include_summary:
                    body = self.read_doclet_content(filepath)
                    snippet_raw = body.strip().replace('\n', ' ')
                    snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                    result_parts.append(f"- {display_name}: {subject}\n  summary: {snippet}")
                else:
                    result_parts.append(f"- {display_name}: {subject}")

        return "\n".join(result_parts)
    
    def list_all(self, verbose: bool = False) -> str:
        """List all doclets with their subjects
        
        Args:
            verbose: If True, include full content of each doclet
        """
        doclets = self.find_all_doclets()
        
        if not doclets:
            return "No doclets found."
        
        result = [f"Total: {len(doclets)} doclets\n"]
        
        # Group by year
        by_year = {}
        for filepath, filename, subject in doclets:
            year = filepath.parent.name
            if year not in by_year:
                by_year[year] = []
            by_year[year].append((filepath, filename, subject))
        
        for year in sorted(by_year.keys(), reverse=True):
            result.append(f"\n{year}:")
            for filepath, filename, subject in by_year[year]:
                display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
                if verbose:
                    # Show full content
                    content = self.read_doclet_content(filepath)
                    result.append(f"\n{'='*70}")
                    result.append(f"File: {display_name}")
                    result.append(f"Subject: {subject}")
                    result.append(f"{'='*70}")
                    result.append(content)
                    result.append(f"{'='*70}\n")
                else:
                    # Just filename and subject
                    result.append(f"  - {display_name}: {subject}")
        
        return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(
        description='Search through doclets using a local LLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "ESP32 networking"
  %(prog)s /path/to/doclets "ESP32 networking"
  %(prog)s --list
  %(prog)s /path/to/doclets --list
  %(prog)s --model llama2 "python async programming"
  %(prog)s --dir /path/to/doclets "topic"
        """
    )
    parser.add_argument('args', nargs='*', help='[doclet_dir] search_query')
    parser.add_argument('--list', '-l', action='store_true', help='List all doclets')
    parser.add_argument('--llm', '--semantic', dest='use_llm', action='store_true', help='Use LLM semantic/fuzzy rerank')
    parser.add_argument('--summary', '--snippets', dest='include_summary', action='store_true', help='Include short summaries/snippets in output')
    parser.add_argument('--dir', '-d', help='Doclets directory (default: current directory)')
    parser.add_argument('--model', '-m', default='llama3.2', help='Ollama model name (default: llama3.2)')
    parser.add_argument('--url', '-u', default='http://localhost:11434', help='Ollama API URL')
    
    args = parser.parse_args()
    
    # Determine doclets directory and query from positional args
    doclets_dir = args.dir
    query_parts = args.args
    file_list_request = False
    
    # If first positional arg looks like path(s), use it as doclets_dir
    # Support comma-separated paths or single path
    if query_parts:
        first_arg = query_parts[0]
        # Expand ~ in path(s) for proper directory/file detection
        if ',' in first_arg:
            expanded_arg = ','.join(str(Path(p).expanduser()) for p in first_arg.split(','))
            first_path = Path(first_arg)  # Keep original for display
        else:
            expanded_arg = str(Path(first_arg).expanduser())
            first_path = Path(expanded_arg)
        
        # Direct file invocation: treat as --list for that file
        if first_path.is_file() and first_path.suffix == '.md':
            file_list_request = True
            doclets_dir = str(first_path.parent)
            query_parts = [first_path.name]
        # Check if it's a comma-separated list or single directory
        elif ',' in first_arg or first_path.is_dir():
            doclets_dir = expanded_arg
            query_parts = query_parts[1:]
    
    # Create manager
    manager = DocletManager(doclets_dir=doclets_dir, ollama_url=args.url)
    manager.model = args.model
    
    if query_parts:
        query = ' '.join(query_parts)
        include_content = args.list or file_list_request
        print(manager.search(query, include_content=include_content, use_llm=args.use_llm, include_summary=args.include_summary))
    elif args.list:
        print(manager.list_all(verbose=True))
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
