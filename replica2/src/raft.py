import time
import random
import threading
import requests

class RaftNode:
    def __init__(self, my_port, peers, node_name, state_machine, on_commit=None):
        self.my_port = my_port
        self.peers = peers
        self.name = node_name
        self.db = state_machine
        self.on_commit = on_commit
        
        self.state = 'FOLLOWER'
        self.current_term = 0
        self.voted_for = None
        self.log = [] 
        
        self.commit_index = -1
        self.last_applied = -1
        
        self.next_index = {p: 0 for p in peers}
        self.match_index = {p: -1 for p in peers}

        self.last_heartbeat = time.time()
        self.timeout = random.uniform(0.5, 0.8) # 500-800ms
        self.lock = threading.Lock()
        
        self.running = True
        threading.Thread(target=self._run_loop, daemon=True).start()

    def replicate(self, stroke):
        if self.state != 'LEADER':
            return False

        with self.lock:
            entry = {'term': self.current_term, 'stroke': stroke}
            self.log.append(entry)
            target_index = len(self.log) - 1
            print(f"[{self.name}] 📝 Logged index {target_index}: {stroke}")

        # Wait for majority commit
        start = time.time()
        while time.time() - start < 2:
            if self.commit_index >= target_index:
                return True 
            time.sleep(0.01)
        
        return False 

    def _run_loop(self):
        while self.running:
            time.sleep(0.02)
            with self.lock:
                elapsed = time.time() - self.last_heartbeat
                
                if self.state == 'FOLLOWER' and elapsed > self.timeout:
                    print(f"[{self.name}] 💀 Timeout! Starting election...")
                    self._start_election()
                
                elif self.state == 'CANDIDATE' and elapsed > self.timeout:
                    print(f"[{self.name}] 💀 Election timeout! Restarting election...")
                    self._start_election()
                
                elif self.state == 'LEADER':
                    if elapsed > 0.15: # 150ms heartbeat
                        self._broadcast_heartbeats()
                        self.last_heartbeat = time.time()
                
                self._apply_logs()

    def _start_election(self):
        self.state = 'CANDIDATE'
        self.current_term += 1
        self.voted_for = self.name
        votes = 1
        self.last_heartbeat = time.time()
        self.timeout = random.uniform(0.5, 0.8) # Reset timeout for split vote
        
        print(f"[{self.name}] 🗳️ Campaigning Term {self.current_term}...")

        # Request votes concurrently to not block
        def request_vote_thread(peer):
            nonlocal votes
            if self._send_request_vote(peer):
                with self.lock:
                    votes += 1
                    if self.state == 'CANDIDATE' and votes > (len(self.peers) + 1) // 2:
                        self._become_leader()

        for peer in self.peers:
            threading.Thread(target=request_vote_thread, args=(peer,), daemon=True).start()

    def _become_leader(self):
        self.state = 'LEADER'
        print(f"[{self.name}] 👑 Elected Leader for Term {self.current_term}")
        for p in self.peers:
            self.next_index[p] = len(self.log)
            self.match_index[p] = -1
        self._broadcast_heartbeats()
        
    def _broadcast_heartbeats(self):
        for peer in self.peers:
            threading.Thread(target=self._send_append_entries, args=(peer,), daemon=True).start()

    def _send_append_entries(self, peer):
        with self.lock:
            if self.state != 'LEADER': return
            
            next_idx = self.next_index[peer]
            entries_to_send = self.log[next_idx:]
            prev_log_index = next_idx - 1
            prev_log_term = self.log[prev_log_index]['term'] if prev_log_index >= 0 else -1

            payload = {
                'term': self.current_term,
                'leader_id': self.name,
                'prev_log_index': prev_log_index,
                'prev_log_term': prev_log_term,
                'entries': entries_to_send,
                'leader_commit': self.commit_index
            }
            
        try:
            url = f"http://{peer}/raft/append_entries"
            res = requests.post(url, json=payload, timeout=0.1)
            data = res.json()
            
            with self.lock:
                if self.state != 'LEADER': return
                if data.get('term', 0) > self.current_term:
                    self.current_term = data['term']
                    self.state = 'FOLLOWER'
                    self.voted_for = None
                    return
                
                if data.get('success'):
                    if entries_to_send:
                        self.next_index[peer] = next_idx + len(entries_to_send)
                        self.match_index[peer] = self.next_index[peer] - 1
                        self._update_commit_index()
                else:
                    if 'conflict_index' in data:
                        # Optimization or just decrement
                        self.next_index[peer] = max(0, self.next_index[peer] - 1)
        except Exception as e:
            pass

    def _update_commit_index(self):
        for N in range(len(self.log) - 1, self.commit_index, -1):
            if self.log[N]['term'] != self.current_term:
                continue
            count = 1
            for p in self.peers:
                if self.match_index[p] >= N:
                    count += 1
            if count > (len(self.peers) + 1) // 2:
                self.commit_index = N
                break

    def _apply_logs(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"[{self.name}] 💾 COMMITTING index {self.last_applied}")
            self.db.append(entry)
            if self.on_commit:
                try:
                    self.on_commit(entry)
                except Exception as e:
                    print("Error in commit callback", e)

    def handle_append_entries(self, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
        with self.lock:
            if term < self.current_term:
                return {'term': self.current_term, 'success': False}
            
            self.current_term = term
            self.state = 'FOLLOWER'
            self.last_heartbeat = time.time()
            
            # Log consistency check
            if prev_log_index >= len(self.log):
                return {'term': self.current_term, 'success': False, 'conflict_index': len(self.log)}
            if prev_log_index >= 0 and self.log[prev_log_index]['term'] != prev_log_term:
                return {'term': self.current_term, 'success': False, 'conflict_index': prev_log_index}

            # Append new entries
            existing_index = prev_log_index + 1
            for entry in entries:
                if existing_index < len(self.log):
                    if self.log[existing_index]['term'] != entry['term']:
                        self.log = self.log[:existing_index]
                        self.log.append(entry)
                else:
                    self.log.append(entry)
                existing_index += 1

            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log) - 1)
            
            return {'term': self.current_term, 'success': True}

    def handle_heartbeat(self, term, leader_id):
        # Explicit heartbeat endpoint
        with self.lock:
            if term < self.current_term:
                return {'term': self.current_term, 'success': False}
            self.current_term = term
            self.state = 'FOLLOWER'
            self.last_heartbeat = time.time()
            return {'term': self.current_term, 'success': True}

    def _send_request_vote(self, peer):
        with self.lock:
            payload = {
                'term': self.current_term, 
                'candidate_id': self.name,
                'last_log_index': len(self.log) - 1,
                'last_log_term': self.log[-1]['term'] if len(self.log) > 0 else -1
            }
        try:
            url = f"http://{peer}/raft/request_vote"
            res = requests.post(url, json=payload, timeout=0.2)
            data = res.json()
            with self.lock:
                if data.get('term', 0) > self.current_term:
                    self.current_term = data['term']
                    self.state = 'FOLLOWER'
                    self.voted_for = None
            return data.get('vote_granted')
        except:
            return False
            
    def handle_request_vote(self, term, candidate_id, last_log_index, last_log_term):
        with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.state = 'FOLLOWER'
                self.voted_for = None
            
            my_last_log_index = len(self.log) - 1
            my_last_log_term = self.log[-1]['term'] if my_last_log_index >= 0 else -1
            
            log_ok = (last_log_term > my_last_log_term) or (last_log_term == my_last_log_term and last_log_index >= my_last_log_index)
            
            if term == self.current_term and (self.voted_for is None or self.voted_for == candidate_id) and log_ok:
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()
                return {'term': self.current_term, 'vote_granted': True}
            
            return {'term': self.current_term, 'vote_granted': False}

    def get_sync_logs(self, from_index):
        with self.lock:
            return self.log[from_index:]
