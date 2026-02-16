"""Git repository reader - SRS FR-16: Incremental scanning via Git diff"""

import re
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
try:
    import git
except ImportError:
    git = None
from .base_reader import BaseReader


class GitReader(BaseReader):
    """Reads source code from a Git repository"""
    
    def __init__(self, repo_path: str, branch: Optional[str] = None, config: Dict[str, Any] = None,
                 incremental: bool = False, ir_store_path: Optional[str] = None):
        super().__init__(config)
        self.repo_path = Path(repo_path)
        self.branch = branch
        self.repo = None
        self.incremental = incremental
        self.ir_store_path = ir_store_path or str(Path("./.techdocgen_ir") / "file_hashes.json")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize and fix common URL issues"""
        # Fix missing slash in protocol (e.g., https:/ -> https://)
        url = re.sub(r'^(https?):/([^/])', r'\1://\2', url)
        url = re.sub(r'^(http?):/([^/])', r'\1://\2', url)
        
        # Ensure URLs ending with .git are preserved
        if url.startswith('http') and not url.endswith('.git') and '/' in url:
            # Check if it looks like a GitHub/GitLab URL that should end with .git
            if 'github.com' in url or 'gitlab.com' in url:
                if not url.endswith('.git') and not url.endswith('/'):
                    url = url.rstrip('/') + '.git'
        
        return url
    
    def _get_clone_path(self, repo_url: str) -> Path:
        """Get the clone path for a repository URL"""
        # Extract repo name from URL
        repo_name = Path(repo_url).stem
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        if not repo_name:
            # Fallback: use last part of URL path
            repo_name = Path(repo_url.rstrip('/').rstrip('.git')).name or "repo"
        return Path("./temp_repos") / repo_name
    
    def _cleanup_existing_clone(self, clone_path: Path):
        """Remove existing clone directory if it exists"""
        if clone_path.exists():
            try:
                # Check if it's a valid git repo
                test_repo = git.Repo(clone_path)
                # If it's valid, we can reuse it, so don't remove
                return False
            except:
                # Not a valid git repo or doesn't exist, remove it
                if clone_path.is_dir():
                    shutil.rmtree(clone_path)
                elif clone_path.exists():
                    clone_path.unlink()
                return True
        return False
    
    def _clone_or_open(self):
        """Clone repository if URL, or open if local path"""
        if git is None:
            raise ImportError("GitPython is required for Git repository support. Install it with: pip install GitPython")
        
        if not self.repo_path.exists():
            # Assume it's a URL
            repo_url = str(self.repo_path)
            
            # Normalize URL to fix common issues
            repo_url = self._normalize_url(repo_url)
            
            # Get clone path
            clone_path = self._get_clone_path(repo_url)
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if clone path already exists and handle it
            if clone_path.exists():
                try:
                    # Try to open existing repo
                    existing_repo = git.Repo(clone_path)
                    print(f"Using existing repository at {clone_path}")
                    self.repo = existing_repo
                    self.repo_path = clone_path
                    # Pull latest changes
                    try:
                        self.repo.remotes.origin.pull()
                        print(f"Updated repository with latest changes")
                    except:
                        print(f"Warning: Could not update repository, using existing version")
                except:
                    # Existing path is not a valid git repo, remove it
                    print(f"Removing invalid existing directory at {clone_path}")
                    self._cleanup_existing_clone(clone_path)
            
            # Clone if we don't have a repo yet
            if self.repo is None:
                # Convert SSH URLs to HTTPS for public repos to avoid SSH config issues
                if repo_url.startswith('git@') or (repo_url.startswith('ssh://')):
                    # Try SSH first, but have HTTPS as fallback
                    try:
                        print(f"Cloning repository from {repo_url}...")
                        self.repo = git.Repo.clone_from(repo_url, str(clone_path))
                        self.repo_path = clone_path
                    except Exception as ssh_error:
                        # Try converting to HTTPS
                        if 'github.com' in repo_url or 'github.ibm.com' in repo_url:
                            https_url = repo_url.replace('git@', 'https://').replace('ssh://git@', 'https://').replace(':', '/')
                            if not https_url.startswith('http'):
                                # Handle git@github.com:user/repo.git format
                                https_url = repo_url.replace('git@', 'https://').replace(':', '/', 1)
                            print(f"SSH clone failed, trying HTTPS: {https_url}")
                            try:
                                # Clean up clone path before retry
                                self._cleanup_existing_clone(clone_path)
                                self.repo = git.Repo.clone_from(https_url, str(clone_path))
                                self.repo_path = clone_path
                            except Exception as https_error:
                                raise ValueError(
                                    f"Failed to clone repository. SSH error: {ssh_error}. "
                                    f"HTTPS error: {https_error}. "
                                    f"Please check your SSH config or use HTTPS URL."
                                )
                        else:
                            raise ValueError(f"Failed to clone repository via SSH: {ssh_error}. "
                                           f"Please check your SSH configuration or use HTTPS URL.")
                else:
                    # HTTPS or other protocol
                    print(f"Cloning repository from {repo_url}...")
                    self.repo = git.Repo.clone_from(repo_url, str(clone_path))
                    self.repo_path = clone_path
        else:
            self.repo = git.Repo(self.repo_path)
        
        # Checkout specific branch if provided
        if self.branch:
            try:
                self.repo.git.checkout(self.branch)
            except:
                print(f"Warning: Could not checkout branch {self.branch}, using current branch")
        
        return self.repo
    
    def read(self) -> List[Dict[str, Any]]:
        """Read all source code files from the Git repository"""
        try:
            self._clone_or_open()
        except Exception as e:
            raise ValueError(f"Failed to access Git repository: {e}")
        
        return list(self.iter_files())

    def _get_changed_files(self) -> Optional[Set[str]]:
        """FR-16: Get set of changed file paths from Git diff (HEAD vs working tree)"""
        if not self.repo or not self.incremental:
            return None
        try:
            changed = set()
            for diff in self.repo.index.diff(None, create_patch=False):
                if diff.a_path:
                    changed.add(diff.a_path)
                if diff.b_path and diff.b_path != diff.a_path:
                    changed.add(diff.b_path)
            for diff in self.repo.index.diff("HEAD", create_patch=False):
                if diff.a_path:
                    changed.add(diff.a_path)
            return changed if changed else None
        except Exception:
            return None
    
    def _should_skip_incremental(self, relative_path: str, content: str) -> bool:
        """Skip file if unchanged (same hash in store)"""
        store = Path(self.ir_store_path)
        if not store.parent.exists():
            return False
        try:
            data = json.loads(store.read_text()) if store.exists() else {}
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            return data.get(relative_path) == file_hash
        except Exception:
            return False
    
    def _update_ir_store(self, relative_path: str, content: str):
        """Update IR store with file hash"""
        store = Path(self.ir_store_path)
        store.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(store.read_text()) if store.exists() else {}
        data[relative_path] = hashlib.sha256(content.encode()).hexdigest()
        store.write_text(json.dumps(data, indent=2))
    
    def iter_files(self):
        """Stream source code files from the Git repository"""
        try:
            self._clone_or_open()
        except Exception as e:
            raise ValueError(f"Failed to access Git repository: {e}")
        
        extensions = self.config.get("extensions", {})
        all_extensions = []
        for exts in extensions.values():
            all_extensions.extend(exts)
        
        # Get repository root
        repo_root = Path(self.repo.working_dir)
        
        # FR-16: Incremental - only yield changed files when enabled
        changed_files = self._get_changed_files() if self.incremental else None
        
        print("Scanning repository for source files...")
        for file_path in repo_root.rglob("*"):
            if not file_path.is_file():
                continue
            
            if file_path.suffix.lower() not in all_extensions:
                continue
            
            rel_path = str(file_path.relative_to(repo_root))
            if changed_files is not None and rel_path not in changed_files:
                continue
            
            if not self._should_include(file_path):
                continue
            
            if self._should_exclude(file_path):
                continue
            
            if not self._is_valid_size(file_path):
                print(f"Warning: File {file_path} exceeds size limit, skipping")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                rel_path = str(file_path.relative_to(repo_root))
                if self.incremental and self._should_skip_incremental(rel_path, content):
                    continue
                
                language = self._detect_language(file_path)
                
                file_info = {
                    "path": str(file_path),
                    "content": content,
                    "language": language,
                    "name": file_path.name,
                    "relative_path": rel_path
                }
                if self.incremental:
                    self._update_ir_store(rel_path, content)
                yield file_info
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue

