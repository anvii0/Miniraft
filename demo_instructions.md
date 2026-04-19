# 🚀 Mini-RAFT Demo Walkthrough

Follow these steps for a perfect presentation. Each section shows exactly what to do and what to tell your teacher.

---

## **Preparation: Setting the Stage**

Before starting, make sure you have Docker running and your terminal open in the project root.

### **Step 1: Start the System**
Run this command to build and start all containers:
```bash
docker compose up --build
```
> [!TIP]
> **What to show:** Open your browser to `http://localhost:8080`. Draw a few lines to show it's working.

---

## **Part 1: Normal Operation (The Log Flow)**

To "wow" your teacher, show the logs while you draw.

### **Step 2: Watch the Logs**
Open a new terminal window and run:
```bash
docker compose logs -f gateway node1 node2 node3
```
*(Alternatively, open 4 separate terminals to show each node clearly.)*

### **Step 3: Draw a Stroke**
1. Draw a line on the canvas.
2. **In the logs, point out:**
   - **Gateway:** `[Gateway] Found Leader: http://nodeX:5000`
   - **Leader:** `[nodeX] 📝 Logged index ...`
   - **Followers:** `[nodeY] 💾 COMMITTING index ...` (when they receive the append entry)
   - **Leader:** `[nodeX] 💾 COMMITTING index ...` (once majority is reached)

---

## **Part 2: Fault Tolerance (Killing the Leader)**

This is the most "Cloud Computing" part of the demo.

### **Step 4: Identify and Kill the Leader**
1. Look at the logs to see who the leader is (it will say `👑 Elected Leader`). Let's say it's `node1`.
2. Stop that specific container:
   ```bash
   docker compose stop node1
   ```

### **Step 5: Watch the Re-election**
1. **In the logs of the other nodes, you will see:**
   - `💀 Timeout! Starting election...`
   - `🗳️ Campaigning Term ...`
   - `👑 Elected Leader for Term ...` (One of the remaining two takes over)
2. **In the Gateway logs:**
   - `[Gateway] ⚠️ No leader found!`
   - (A few seconds later) `[Gateway] Found Leader: http://nodeY:5000`

### **Step 6: Resume Drawing**
Draw something in the browser. It should still work! This proves the system survived a leader crash.

---

## **Part 3: Zero-Downtime Hot-Reload**

Show how you can update code without stopping the world.

### **Step 7: Bring Node 1 back**
```bash
docker compose start node1
```
Watch it catch up and sync logs automatically.

### **Step 8: Edit a Python File**
1. Keep the logs running.
2. Open `replica1/src/server.py` and change the welcome message on line 14:
   - Change: `print(f"🚀 Starting {node_name} on port {my_port}")`
   - To: `print(f"🔥 HOT RELOAD: Starting {node_name} on port {my_port}")`
3. Save the file.

### **Step 9: Observe the Restart**
1. Look at the `node1` logs. You will see it instantly restart due to `watchmedo`.
2. Draw something. The system continues seamlessly. This is exactly how modern microservices handle updates (Blue-Green/Rolling deployments).

---

## **Summary Commands Cheat Sheet**

| Action | Command |
| :--- | :--- |
| **Start Everything** | `docker compose up --build` |
| **Stop Everything** | `docker compose down` |
| **View All Logs** | `docker compose logs -f` |
| **Stop a Node** | `docker compose stop node1` (replace with leader name) |
| **Restart a Node** | `docker compose start node1` |
| **View History (API)** | `curl http://localhost:5001/history` |
