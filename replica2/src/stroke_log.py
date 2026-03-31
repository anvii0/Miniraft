import os
import json
import threading

class StrokeLog:
    def __init__(self, name, log_file='/data/strokes.log'):
        self.name = name
        self.log_file = log_file
        self.lock = threading.Lock()
        
        # Memory state
        self.strokes = []
        
        self._recover()

    def _recover(self):
        """Reads WAL and restores state."""
        if not os.path.exists(self.log_file):
            return
            
        print(f"[{self.name}] 🔄 Recovering strokes from disk...")
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    self.strokes.append(entry)
                except ValueError:
                    continue
        print(f"[{self.name}] ✅ Recovery complete. Total strokes: {len(self.strokes)}")

    def _append_to_wal(self, entry):
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def append(self, entry):
        """Called by RAFT when a log entry is committed."""
        with self.lock:
            self._append_to_wal(entry)
            self.strokes.append(entry)
            print(f"[{self.name}] 🎨 Saved stroke to log. Total: {len(self.strokes)}")
            return True

    def get_all(self):
        return self.strokes
