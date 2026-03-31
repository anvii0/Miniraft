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

## Stopping the Server
When you're done, tear down the environment by running:
```bash
docker compose down
```
