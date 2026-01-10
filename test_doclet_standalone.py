#!/usr/bin/env python3
"""
Standalone test of DocletManager diagnostics
"""
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union

class DocletManager():
    def __init__(self, doclets_dir: str = None, ollama_url: str = "http://localhost:11434"): # type: ignore
        """Initialize the doclet manager
        
        Args:
            doclets_dir: Root directory or comma-separated list of directories containing year folders
            ollama_url: URL of the local Ollama API
        """
        # Support comma-separated list of directories
        if doclets_dir:
            paths = [p.strip() for p in doclets_dir.split(',')]
            # Expand ~ in each path
            self.doclets_dirs = [Path(p).expanduser() for p in paths]
        else:
            self.doclets_dirs = [Path(__file__).parent]
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # Default model, can be changed
        print(f"DocletManager.__init__ raw input: {doclets_dir}")
        print(f"DocletManager initialized with directories: {[str(d) for d in self.doclets_dirs]}")
        for d in self.doclets_dirs:
            print(f"  Directory exists: {d.exists()}, is_dir: {d.is_dir()}")
        
    def find_all_doclets(self) -> List[Tuple[Path, str, str]]:
        """Find all doclets in the directory structure
        
        Returns:
            List of tuples: (filepath, filename, subject_line)
        """
        doclets = []
        
        # Search across all configured directories
        for base_dir in self.doclets_dirs:
            print(f"  Searching in: {base_dir}")
            year_count = 0
            # Look for year folders (e.g., 2026, 2025, etc.)
            for year_folder in base_dir.glob("[0-9][0-9][0-9][0-9]"):
                year_count += 1
                print(f"    Found year folder: {year_folder.name}")
                if year_folder.is_dir():
                    # Find all .md files in this year folder
                    for doclet_file in year_folder.glob("*.md"):
                        # Read the subject line (first line starting with '# ')
                        try:
                            with open(doclet_file, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                subject = first_line[2:].strip() if first_line.startswith('# ') else "No subject"
                                doclets.append((doclet_file, doclet_file.name, subject))
                                print(f"      Added: {doclet_file.name} - {subject}")
                        except Exception as e:
                            print(f"Warning: Could not read {doclet_file}: {e}", file=sys.stderr)
            if year_count == 0:
                print(f"    No year folders found in {base_dir}")
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

    def read_doclet_content(self, filepath: Path) -> str:
        """Read the full content of a doclet file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

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
        print(f"  Searching for '{query_lower}' in {len(doclets)} doclets...")
        for filepath, fname, subject in doclets:
            subj_lower = subject.lower()
            body_lower = self.read_doclet_content(filepath).lower()
            haystack = subj_lower + "\n" + body_lower
            if query_lower in haystack:
                print(f"    MATCH: {fname}")
                deterministic_matches.append((filepath, fname, subject))

        matching_files = deterministic_matches

        meta["match_count"] = len(matching_files)
        meta["matched_by"] = "deterministic"

        if not matching_files:
            meta["status"] = "no_matches"
            return [], "no_matches", meta

        meta["status"] = "ok"
        return matching_files, None, meta

    def search_data(self, query: str, include_content: bool = False, use_llm: bool = False, include_summary: bool = False, return_meta: bool = False) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
        """Programmatic search returning raw data; optionally include metadata."""
        print(f"search_data called with query: '{query}'")
        matches, error, meta = self._match_doclets(query=query, use_llm=use_llm)
        print(f"  _match_doclets returned: error={error}, match_count={meta.get('match_count')}, status={meta.get('status')}")

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


if __name__ == '__main__':
    print("=" * 70)
    print("Testing DocletManager Diagnostics")
    print("=" * 70)
    
    manager = DocletManager(doclets_dir='~/Doclets/Doclets,~/Doclets/EasyCoder,~/Doclets/RBR')
    
    print("\n" + "=" * 70)
    print("Searching for 'api'...")
    print("=" * 70)
    results, meta = manager.search_data('api', return_meta=True)
    print(f"\nResults: {len(results)} matches")
    print(f"Metadata: {meta}")
    for r in results:
        print(f"  - {r['display_filename']}: {r['subject']}") # type: ignore
