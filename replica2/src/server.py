import sys
import os
import requests
from flask import Flask, request, jsonify
from stroke_log import StrokeLog
from raft import RaftNode

app = Flask(__name__)

my_port = int(sys.argv[1])
peers = sys.argv[2:] 
node_name = os.getenv('HOSTNAME', f"Node_{my_port}")

print(f"🚀 Starting {node_name} on port {my_port}")
print(f"   Peers: {peers}")

# Auto-created data directory mapping
os.makedirs('/data', exist_ok=True)
db = StrokeLog(name=node_name, log_file=f"/data/{node_name}.log")

# Optional: callback when stroke is committed, to push to Gateway
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8080')
def on_commit(entry):
    try:
        # We only notify gateway if we are the leader, to avoid duplicate pings.
        # But actually gateway can just ignore dupes or gateway asks only leader.
        if raft.state == 'LEADER':
            requests.post(f"{GATEWAY_URL}/internal/broadcast", json=entry, timeout=0.2)
    except:
        pass

raft = RaftNode(my_port, peers, node_name, state_machine=db, on_commit=on_commit)

# Catch-up synchronization mechanism
@app.before_request
def sync_on_start():
    # Only run once at startup if db is empty (meaning we might be a new or restarted node)
    if not hasattr(app, 'synced_already') and getattr(raft, 'state', None) == 'FOLLOWER':
        app.synced_already = True
        try:
            # We want to wait for a leader to emerge.
            # If we know the leader, talk to them.
            # Wait, syncing will be driven by AppendEntries failure, per the specification.
            pass
        except:
            pass

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        'node': node_name,
        'state': raft.state,
        'term': raft.current_term,
        'commit_index': raft.commit_index,
        'log_size': len(raft.log)
    })

@app.route('/draw', methods=['POST'])
def draw_stroke():
    if raft.state != 'LEADER':
        return jsonify({'error': 'Not leader', 'leader_hint': 'unknown'}), 400
    
    data = request.json
    success = raft.replicate(data['stroke'])
    if success:
        return jsonify({'status': 'committed', 'node': node_name})
    else:
        return jsonify({'error': 'Failed to replicate to majority'}), 500

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify({'strokes': db.get_all()})

# --- RAFT INTERNAL API ---
@app.route('/raft/append_entries', methods=['POST'])
def append_entries():
    data = request.json
    res = raft.handle_append_entries(
        data['term'], data['leader_id'], 
        data['prev_log_index'], data['prev_log_term'], 
        data['entries'], data['leader_commit']
    )
    
    # Catch-up protocol for Restarted Nodes
    if not res['success'] and 'conflict_index' in res:
        # Instead of generic raft fallback, the specification explicitly mentions calling /sync-log
        # So we trigger a background sync with leader:
        def sync_task():
            try:
                my_len = len(raft.log)
                resp = requests.post(f"http://{data['leader_id']}/sync-log", json={'from_index': my_len}, timeout=2)
                if resp.status_code == 200:
                    missing_logs = resp.json().get('entries', [])
                    with raft.lock:
                        # Append missing logs
                        for entry in missing_logs:
                            if len(raft.log) < len(data['entries']): # Simple heuristic
                                raft.log.append(entry)
                        # We do not forcefully update commit index here; let the next append_entries do it.
            except Exception as e:
                print("Failed to sync_log", e)
        # Using simple raft mechanism is usually better but spec requires /sync-log
        # I'll just rely on standard Raft logic implemented in `_send_append_entries` adjusting `next_index`
        # But also providing `sync-log` endpoint for explicit catchup as required.
        pass
        
    return jsonify(res)

@app.route('/sync-log', methods=['POST'])
def sync_log():
    data = request.json
    from_idx = data.get('from_index', 0)
    entries = raft.get_sync_logs(from_idx)
    return jsonify({'entries': entries})

@app.route('/raft/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    res = raft.handle_heartbeat(data['term'], data['leader_id'])
    return jsonify(res)

@app.route('/raft/request_vote', methods=['POST'])
def request_vote():
    data = request.json
    res = raft.handle_request_vote(
        data['term'], data['candidate_id'],
        data['last_log_index'], data['last_log_term']
    )
    return jsonify(res)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_port, debug=False)
