# Distributed Real-Time Drawing Board with Mini-RAFT

A fault-tolerant, highly available distributed drawing board built with WebSockets, Node.js, Python, and a RAFT-like consensus protocol. 

## System Architecture

- **Gateway Node**: A WebSocket API server orchestrating browser clients.
- **Replica Nodes (3x)**: Python distributed replicas executing a MiniRAFT consensus protocol. Ensures that your drawn strokes are preserved securely across the cluster.
- **Frontend Panel**: A beautiful, glassmorphic UI connected directly to the WebSocket Gateway.

## How to Run Locally

If you've closed the application and turned off Docker, here is exactly how to start it back up:

1. **Open Docker Desktop**
   - Ensure the Docker Daemon is running fully before proceeding. You should see the Docker whale icon in your Mac's menu bar indicating it is active.

2. **Open your Terminal**
   - Navigate to the project directory:
     ```bash
     cd /Users/anvitakulkarni/Desktop/miniraft
     ```

3. **Start the Cluster**
   - Run the following command to recreate and launch the distributed cluster in the background:
     ```bash
     docker compose up --build -d
     ```
    - Start only selected services (same compose file):
       ```bash
       docker compose up --build -d gateway node1 node2 node3
       ```
    - Use `-f` only to specify the compose file:
       ```bash
       docker compose -f docker-compose.yml up --build -d gateway node1 node2 node3
       ```
   - *Wait a couple of seconds for the gateway to locate the new elected Python Replica Leader.*

4. **Open the Drawing Board**
   - Head over to your browser and visit:
     **[http://localhost:8080](http://localhost:8080)**
   - Open this link in **multiple windows or incognito tabs** to see real-time stroke syncing!

## How to Test Failover & Zero-Downtime Hot Reload

Because the implementation folders are bind-mounted and monitored by `watchdog` inside the Docker containers:
- You can open the `replica1/src/server.py` file, make a small edit, and hit **Save**. 
- The target Python Replica container will instantly restart to reflect changes. 
- A new leader election will be brokered silently without the Web Browser clients ever disconnecting from the Node.js Gateway.

## Leader Election and Failover Commands (Quick README)

Use this exact sequence when you want to see who the leader is, kill it, and watch a new leader get elected.

1. **Go to project root**
   ```bash
   cd /Users/anvitakulkarni/Desktop/miniraft
   ```

2. **Start the cluster**
   ```bash
   docker compose up --build -d
   ```

   Start specific services directly:
   ```bash
   docker compose up --build -d gateway node1 node2 node3
   ```

   Note: `-f` is for file selection (for example `docker-compose.yml`), not service names.

3. **Watch all service logs**
   ```bash
   docker compose logs -f gateway node1 node2 node3
   ```
   Look for lines like:
   - `👑 Elected Leader for Term ...` (inside node logs)
   - `[Gateway] Found Leader: http://nodeX:5000` (inside gateway logs)

4. **Optional: confirm from browser**
   - Open [http://localhost:8080](http://localhost:8080) and draw.
   - Strokes should replicate while leader is healthy.

5. **Kill the current leader**
   Replace `node1` with whichever node is currently leader.
   ```bash
   docker compose stop node1
   ```

6. **Observe new leader election**
   In the logs, you should see:
   - `💀 Timeout! Starting election...`
   - `🗳️ Campaigning Term ...`
   - `👑 Elected Leader for Term ...`
   - Gateway briefly: `[Gateway] ⚠️ No leader found!`
   - Then gateway recovers: `[Gateway] Found Leader: http://nodeY:5000`

7. **Bring the old node back**
   ```bash
   docker compose start node1
   ```
   It should rejoin and catch up as a follower.

8. **Stop everything when done**
   ```bash
   docker compose down
   ```

### Extra Helpful Commands

- Show running containers:
  ```bash
  docker ps
  ```

- Watch just gateway logs:
  ```bash
  docker compose logs -f gateway
  ```

- Watch just one replica:
  ```bash
  docker compose logs -f node1
  ```

- Check stroke history from a replica API:
  ```bash
  curl http://localhost:5001/history
  ```

## Stopping the Server
When you're done, tear down the environment by running:
```bash
docker compose down
```
