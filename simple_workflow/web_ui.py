from helpers.ui_manager import ui_manager
import time
import signal
import sys

def signal_handler(sig, frame):
    print("\n\n🛑 Shutting down UI server...")
    ui_manager.stop()
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    if ui_manager.start():
        ui_manager.show_ui_link()
        print("\n💡 Press Ctrl+C to stop the UI server\n")
        try:
            # Keep the script running to keep the UI server alive
            while True:
                if ui_manager.ui_process:
                    exit_code = ui_manager.ui_process.poll()
                    if exit_code is not None:
                        print(f"\n⚠️  UI server process has stopped (exit code: {exit_code})")
                        with ui_manager.output_lock:
                            if ui_manager.process_output:
                                print("\n📋 Last output (last 30 lines):")
                                print('\n'.join(ui_manager.process_output[-30:]))
                        print("\n💡 The UI server has stopped. Check the output above for errors.")
                        print("   Make sure your NAT backend server is running on port 8000")
                        break
                else:
                    print("\n⚠️  UI process is None - something went wrong")
                    break
                time.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        print("❌ Failed to start UI server")
        sys.exit(1)
