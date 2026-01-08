#!/usr/bin/env python3
"""
NAT UI Manager - Robust UI launcher with error handling and validation
"""
import subprocess
import time
import os
import sys
import atexit
import socket
import shutil
import threading
import importlib
from pathlib import Path

class UIManager:
    """Manages the NAT UI server lifecycle with robust error handling."""
    
    def __init__(self):
        # Get the directory where this script is located (simple_workflow/helpers/)
        # Then go up one level to get to simple_workflow/, and then to project root
        script_dir = Path(__file__).parent.parent
        project_root = script_dir.parent
        
        # Check for existing UI folder: prefer root, then simple_workflow
        root_ui_path = project_root / "NeMo-Agent-Toolkit-UI"
        local_ui_path = script_dir / "NeMo-Agent-Toolkit-UI"
        
        if root_ui_path.exists() and root_ui_path.is_dir():
            self.ui_path = root_ui_path
        elif local_ui_path.exists() and local_ui_path.is_dir():
            self.ui_path = local_ui_path
        else:
            # Default to simple_workflow if neither exists (will clone there)
            self.ui_path = local_ui_path
        
        self.ui_process = None
        self.ui_port = 3000
        self.nat_port = 8000
        self.process_output = []  # Store recent output lines
        self.output_lock = threading.Lock()
        
        # Register cleanup on exit
        atexit.register(self._cleanup)
    
    def _get_command_path(self, command):
        """Get the full path to a command, handling Microsoft Windows .cmd/.bat files."""
        if sys.platform == "win32":
            # On Microsoft Windows, try to find the command in PATH
            cmd_path = shutil.which(command)
            if cmd_path:
                return cmd_path
            # Try with .cmd extension (common on Microsoft Windows)
            cmd_path = shutil.which(f"{command}.cmd")
            if cmd_path:
                return cmd_path
            # Try with .bat extension
            cmd_path = shutil.which(f"{command}.bat")
            if cmd_path:
                return cmd_path
            # If not found, return original command (will be handled by shell=True)
            return command
        else:
            # On Unix-like systems, return the command as-is
            return command
    
    def _get_npx_path(self):
        """Get npx command path, falling back to npm if npx not available."""
        npx_path = self._get_command_path("npx")
        if npx_path != "npx" or shutil.which("npx"):
            return npx_path
        # Fallback to npm exec if npx not available
        npm_path = self._get_command_path("npm")
        return f"{npm_path} exec --"
    
    def _check_command_exists(self, command):
        """Check if a command is available."""
        # On Microsoft Windows, use shell=True to properly handle .cmd/.bat files
        if sys.platform == "win32":
            cmd_path = self._get_command_path(command)
            try:
                subprocess.run(f'"{cmd_path}" --version', 
                              shell=True,
                              capture_output=True, 
                              check=True, 
                              timeout=5)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return False
        else:
            # On Unix-like systems, use the original approach
            try:
                subprocess.run([command, "--version"], 
                              capture_output=True, check=True, timeout=5)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return False
    
    def _check_port_available(self, port):
        """Check if a port is available."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', port))
            return result != 0  # Port is available if connection fails
        finally:
            sock.close()
    
    def _wait_for_port(self, port, timeout=60):
        """Wait for a port to become active."""
        print(f"⏳ Waiting for service on port {port}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self._check_port_available(port):
                return True
            time.sleep(2)
        return False
    
    def _cleanup(self):
        """Cleanup on exit."""
        if self.ui_process and self.ui_process.poll() is None:
            self.ui_process.terminate()
            try:
                self.ui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ui_process.kill()
    
    def start(self):
        """Start the UI server with comprehensive error handling."""
        try:
            # 1. Validate prerequisites
            print("🔍 Checking prerequisites...")
            
            if not self._check_command_exists("git"):
                raise RuntimeError("❌ git is not installed")
            
            if not self._check_command_exists("node"):
                raise RuntimeError("❌ Node.js is not installed")
            
            if not self._check_command_exists("npm"):
                raise RuntimeError("❌ npm is not installed")
            
            print("✅ All prerequisites found")
            
            # 2. Verify NAT server is running
            print(f"🔍 Checking NAT server on port {self.nat_port}...")
            if self._check_port_available(self.nat_port):
                print(f"⚠️  Warning: NAT server doesn't appear to be running on port {self.nat_port}")
                print("   The UI may not work properly without it")
            else:
                print(f"✅ NAT server detected on port {self.nat_port}")
            
            # 3. Check if UI port is available
            if not self._check_port_available(self.ui_port):
                print(f"⚠️  Port {self.ui_port} is already in use")
                if sys.platform != "win32":
                    # Only offer to kill on Unix-like systems (Microsoft Windows requires different commands)
                    response = input(f"   Try to kill existing process on port {self.ui_port}? (y/n): ")
                    if response.lower() == 'y':
                        try:
                            subprocess.run(f"lsof -ti:{self.ui_port} | xargs kill -9 2>/dev/null || "
                                         f"fuser -k {self.ui_port}/tcp 2>/dev/null || true",
                                         shell=True, timeout=5)
                            time.sleep(2)
                            if not self._check_port_available(self.ui_port):
                                raise RuntimeError(f"❌ Failed to free port {self.ui_port}")
                        except Exception:
                            raise RuntimeError(f"❌ Port {self.ui_port} is in use and could not be freed")
                else:
                    raise RuntimeError(f"❌ Port {self.ui_port} is already in use. Please stop the process using it manually.")
            
            # 4. Check for UI repo - use existing if found, clone if needed
            if not self.ui_path.exists():
                print("📥 Cloning NAT UI repository...")
                try:
                    # Clone into the target directory explicitly
                    subprocess.run(
                        ["git", "clone", 
                         "https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI.git",
                         str(self.ui_path)],
                        check=True,
                        timeout=120,
                        capture_output=True
                    )
                    print("✅ UI repository cloned")
                except subprocess.TimeoutExpired:
                    raise RuntimeError("❌ Git clone timed out - check your internet connection")
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode() if e.stderr else str(e)
                    raise RuntimeError(f"❌ Failed to clone repository: {error_msg}")
            else:
                print(f"✅ UI repository already exists at {self.ui_path}")
            
            # 5. Install dependencies with retry
            print("📦 Installing UI dependencies...")
            max_retries = 2
            npm_cmd = self._get_command_path("npm")
            use_npm_install = False  # Flag to switch to npm install if npm ci fails
            use_legacy_peer_deps = False  # Flag to use --legacy-peer-deps for peer dependency conflicts
            
            for attempt in range(max_retries):
                try:
                    # Try npm ci first (faster, more reliable), fall back to npm install if lockfile is out of sync
                    install_cmd = "install" if use_npm_install else "ci"
                    extra_flags = " --legacy-peer-deps" if use_legacy_peer_deps else ""
                    
                    if sys.platform == "win32":
                        result = subprocess.run(
                            f'"{npm_cmd}" {install_cmd}{extra_flags}',
                            cwd=self.ui_path,
                            shell=True,
                            check=True,
                            timeout=180,
                            capture_output=True,
                            text=True
                        )
                    else:
                        cmd_list = [npm_cmd, install_cmd]
                        if use_legacy_peer_deps:
                            cmd_list.append("--legacy-peer-deps")
                        result = subprocess.run(
                            cmd_list,
                            cwd=self.ui_path,
                            check=True,
                            timeout=180,
                            capture_output=True,
                            text=True
                        )
                    print("✅ Dependencies installed")
                    break
                except subprocess.TimeoutExpired:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Install timed out, retrying ({attempt + 1}/{max_retries})...")
                    else:
                        raise RuntimeError("❌ npm install timed out after retries")
                except subprocess.CalledProcessError as e:
                    # Check if it's a lockfile mismatch error - if so, try npm install instead
                    error_output = (e.stderr or "") + (e.stdout or "")
                    if not use_npm_install and ("package-lock.json" in error_output.lower() or 
                                                 "lockfile" in error_output.lower() or
                                                 "cannot be installed" in error_output.lower()):
                        print("⚠️  package-lock.json is out of sync, switching to 'npm install'...")
                        use_npm_install = True
                        continue  # Retry with npm install
                    
                    # Check if it's a peer dependency conflict - if so, try with --legacy-peer-deps
                    if not use_legacy_peer_deps and ("eresolve" in error_output.lower() or 
                                                      "peer dependency" in error_output.lower() or
                                                      "conflicting peer dependency" in error_output.lower()):
                        print("⚠️  Peer dependency conflict detected, retrying with --legacy-peer-deps...")
                        use_legacy_peer_deps = True
                        continue  # Retry with --legacy-peer-deps
                    
                    # Build comprehensive error message
                    error_msg = f"❌ Failed to install dependencies:\n"
                    if e.stderr:
                        error_msg += f"\nSTDERR:\n{e.stderr}\n"
                    if e.stdout:
                        error_msg += f"\nSTDOUT:\n{e.stdout}\n"
                    if not e.stderr and not e.stdout:
                        error_msg += f"\n(Process exited with code {e.returncode})\n"
                        error_msg += "Try running 'npm install' manually in the NeMo-Agent-Toolkit-UI directory to see the full error.\n"
                    
                    if attempt < max_retries - 1:
                        print(f"⚠️  Install failed, retrying ({attempt + 1}/{max_retries})...")
                        print(error_msg)
                    else:
                        raise RuntimeError(error_msg)
            
            # 6. Configure .env file
            print("⚙️  Configuring environment...")
            env_file = self.ui_path / ".env"
            nat_backend_url = f"http://localhost:{self.nat_port}"
            
            # Read existing .env if it exists
            env_vars = {}
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
            
            # Update/ensure required UI variables
            env_vars['NAT_BACKEND_URL'] = nat_backend_url
            if 'PORT' not in env_vars:
                env_vars['PORT'] = str(self.ui_port)
            
            # Write .env file (only in UI directory)
            with open(env_file, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            # Verify .env file was written correctly
            if not env_file.exists():
                raise RuntimeError(f"❌ Failed to create .env file at {env_file}")
            
            print(f"✅ Environment configured (NAT_BACKEND_URL={nat_backend_url}, .env at {env_file})")
            
            # 7. Start UI server
            print("🎨 Starting UI development server...")
            try:
                npm_cmd = self._get_command_path("npm")
                node_cmd = self._get_command_path("node")
                npx_cmd = self._get_command_path("npx")
                
                # On Microsoft Windows, commands must be run directly because package.json uses
                # Unix-style env var syntax (NEXT_TELEMETRY_DISABLED=1) which doesn't work on Microsoft Windows
                # Use npx concurrently to run both processes with proper Microsoft Windows env handling
                if sys.platform == "win32":
                    # Use command names directly (node, npx) since they're in PATH
                    # This avoids issues with spaces in paths like "C:\Program Files\..."
                    dev_cmd = (
                        'npx concurrently '
                        '--kill-others --names "UI" -c "bgBlue.bold" --hide 1 '
                        '"node proxy/server.js" '
                        '"npx next dev -p 3099"'
                    )
                    self.ui_process = subprocess.Popen(
                        dev_cmd,
                        cwd=self.ui_path,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,  # Capture stderr separately
                        text=True,
                        bufsize=1,  # Line buffered
                        env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}
                    )
                else:
                    # On Unix, use npm run dev as it works correctly
                    self.ui_process = subprocess.Popen(
                        [npm_cmd, "run", "dev"],
                        cwd=self.ui_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,  # Capture stderr separately
                        text=True,
                        bufsize=1,  # Line buffered
                        env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}
                    )
                
                # Start threads to capture both stdout and stderr
                def capture_stdout():
                    if self.ui_process and self.ui_process.stdout:
                        for line in iter(self.ui_process.stdout.readline, ''):
                            if not line:
                                break
                            line_clean = line.rstrip()
                            # Print important lines immediately for debugging
                            if any(keyword in line_clean for keyword in ['ERROR:', 'error', 'Failed', 'failed', 'exited with code']):
                                print(f"⚠️  [STDOUT] {line_clean}")
                            with self.output_lock:
                                self.process_output.append(f"[STDOUT] {line_clean}")
                                # Keep only last 100 lines for better debugging
                                if len(self.process_output) > 100:
                                    self.process_output.pop(0)
                
                def capture_stderr():
                    if self.ui_process and self.ui_process.stderr:
                        for line in iter(self.ui_process.stderr.readline, ''):
                            if not line:
                                break
                            line_clean = line.rstrip()
                            # Always print stderr as it contains errors
                            print(f"⚠️  [STDERR] {line_clean}")
                            with self.output_lock:
                                self.process_output.append(f"[STDERR] {line_clean}")
                                # Keep only last 100 lines for better debugging
                                if len(self.process_output) > 100:
                                    self.process_output.pop(0)
                
                stdout_thread = threading.Thread(target=capture_stdout, daemon=True)
                stderr_thread = threading.Thread(target=capture_stderr, daemon=True)
                stdout_thread.start()
                stderr_thread.start()
                
            except Exception as e:
                raise RuntimeError(f"❌ Failed to start UI server: {e}")
            
            # 8. Wait for both ports to be ready (gateway on 3000, Next.js on 3099)
            # Give the process a moment to start and potentially show errors
            time.sleep(3)
            
            # Check if process already crashed
            if self.ui_process.poll() is not None:
                with self.output_lock:
                    recent_output = '\n'.join(self.process_output[-50:])
                error_msg = "❌ UI server process exited before gateway could start:\n"
                if recent_output:
                    error_msg += f"\nRecent output (last 50 lines):\n{recent_output}\n"
                # Check for common error patterns in output
                error_lines = [line for line in self.process_output if any(keyword in line for keyword in ["ERROR:", "error", "Failed", "failed", "exited with code", "EADDRINUSE"])]
                if error_lines:
                    error_msg += f"\n🔍 Error messages found:\n" + '\n'.join(error_lines[-15:]) + "\n"
                raise RuntimeError(error_msg)
            
            print(f"⏳ Waiting for gateway on port {self.ui_port}...")
            gateway_ready = self._wait_for_port(self.ui_port, timeout=30)
            
            if gateway_ready:
                # Double-check process is still running
                if self.ui_process.poll() is not None:
                    with self.output_lock:
                        recent_output = '\n'.join(self.process_output[-30:])
                    raise RuntimeError(f"❌ Gateway started but process exited immediately. Output:\n{recent_output}")
                print(f"✅ Gateway ready on port {self.ui_port}")
            else:
                # Check if process crashed
                if self.ui_process.poll() is not None:
                    with self.output_lock:
                        recent_output = '\n'.join(self.process_output[-50:])
                    error_msg = "❌ UI server crashed during startup:\n"
                    if recent_output:
                        error_msg += f"\nRecent output (last 50 lines):\n{recent_output}\n"
                    # Check for common error patterns in output
                    error_lines = [line for line in self.process_output if any(keyword in line for keyword in ["ERROR:", "error", "Failed", "failed", "exited with code", "EADDRINUSE"])]
                    if error_lines:
                        error_msg += f"\n🔍 Error messages found:\n" + '\n'.join(error_lines[-15:]) + "\n"
                    raise RuntimeError(error_msg)
                else:
                    raise RuntimeError(f"❌ Gateway did not start on port {self.ui_port} within 30 seconds")
            
            # Check Next.js dev server on port 3099
            print("⏳ Waiting for Next.js dev server on port 3099...")
            nextjs_ready = self._wait_for_port(3099, timeout=60)
            
            if nextjs_ready:
                print("✅ Next.js dev server ready on port 3099")
                # Wait for Next.js to finish compiling the root page
                print("⏳ Waiting for Next.js to finish initial compilation...")
                max_wait = 60  # Maximum 60 seconds
                start_time = time.time()
                compiled = False
                
                while time.time() - start_time < max_wait:
                    time.sleep(2)
                    with self.output_lock:
                        recent_output = '\n'.join(self.process_output[-10:])
                        # Check if compilation is complete
                        # Look for "✓ Compiled" or "Compiled in" (success) but not "○ Compiling" (still compiling)
                        if ('✓ Compiled' in recent_output or 'Compiled in' in recent_output) and '○ Compiling' not in recent_output:
                            compiled = True
                            break
                        # Note: Check for errors but don't act on them here since compilation might still succeed
                    
                    # Also check if process crashed
                    if self.ui_process.poll() is not None:
                        break
                
                if compiled:
                    print("✅ Next.js compilation complete")
                else:
                    print("⚠️  Next.js may still be compiling - this is normal for first startup")
                
                # Verify Next.js is actually responding on port 3099
                print("🔍 Verifying Next.js is responding on port 3099...")
                for attempt in range(5):
                    try:
                        import urllib.request
                        response = urllib.request.urlopen("http://localhost:3099", timeout=5)
                        if response.getcode() in [200, 404]:  # 404 is OK, means server is responding
                            print("✅ Next.js is responding on port 3099")
                            break
                    except Exception as e:
                        if attempt < 4:
                            time.sleep(2)
                        else:
                            print(f"⚠️  Next.js not responding on port 3099: {e}")
                            print("   This may cause the gateway to show 'Next.js dev server unavailable'")
                            # Show recent output to help debug
                            with self.output_lock:
                                if self.process_output:
                                    print("\n📋 Recent Next.js output (last 15 lines):")
                                    nextjs_lines = [line for line in self.process_output if '[1]' in line or 'next' in line.lower()]
                                    print('\n'.join(nextjs_lines[-15:]) if nextjs_lines else '\n'.join(self.process_output[-15:]))
            else:
                # Don't fail completely, but warn
                print("⚠️  Warning: Next.js dev server may not be ready yet")
                print("   The UI may take a moment to fully start")
            
            # Final process health check
            if self.ui_process.poll() is not None:
                with self.output_lock:
                    recent_output = '\n'.join(self.process_output[-30:])
                error_msg = "❌ UI server process has crashed:\n"
                if recent_output:
                    error_msg += f"\nRecent output (last 30 lines):\n{recent_output}\n"
                raise RuntimeError(error_msg)
            
            print(f"✅ UI started successfully on port {self.ui_port}")
            return True
            
        except RuntimeError as e:
            print(str(e))
            self.stop()
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the UI server gracefully."""
        if self.ui_process:
            print("🛑 Stopping UI server...")
            try:
                self.ui_process.terminate()
                self.ui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing UI server...")
                self.ui_process.kill()
            finally:
                self.ui_process = None
            print("✅ UI server stopped")
    
    def get_status(self):
        """Get current status of UI server."""
        if self.ui_process is None:
            return "Not started"
        elif self.ui_process.poll() is None:
            return f"Running (PID: {self.ui_process.pid})"
        else:
            return f"Stopped (exit code: {self.ui_process.poll()})"
    
    def show_ui_link(self):
        """Display a clickable link to the UI."""
        # Check if UI is actually running
        if not self._check_port_available(self.ui_port):
            status = "✅ Running"
        else:
            status = "⚠️  Not responding"
        
        # Try to use IPython.display if available (Jupyter environment)
        # Otherwise fall back to terminal-friendly output
        try:
            ipython_display = importlib.import_module('IPython.display')
            HTML = ipython_display.HTML
            display = ipython_display.display
            
            html_content = f'''
            <div style="padding: 20px; background-color: #f0f8ff; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; color: #0066cc;">🚀 NAT UI Demo</h3>
                <p style="margin: 10px 0;">Experience your climate agent with a production-ready interface!</p>
                <p style="margin: 10px 0;">
                    Status: <strong>{status}</strong> | 
                    Port: <code style="background: #e0e0e0; padding: 2px 6px; border-radius: 3px;">{self.ui_port}</code>
                </p>
                <p style="margin: 10px 0;">
                    <strong>Local access:</strong> 
                    <a href="http://localhost:{self.ui_port}" target="_blank">http://localhost:{self.ui_port}</a>
                </p>
                <p style="margin-top: 15px; font-size: 0.9em; color: #666;">
                    💡 Tip: Try asking questions like "What's the temperature trend in France?"
                </p>
            </div>
            '''
            
            display(HTML(html_content))
            
        except ImportError:
            # Terminal-friendly output when IPython is not available
            print(f"\n📍 UI Status: {status}")
            print(f"📍 Access the UI at: http://localhost:{self.ui_port}")
            print("💡 Tip: Try asking questions like 'What's the weather like in Sydney, Australia?'")

# Create a global instance
ui_manager = UIManager()
