# Vercel Deployment Plan - Queue Cure '26

The user requested to deploy the application on **Vercel**. 

## ⚠️ Architectural Warning (Persistent WebSockets on Vercel)
Vercel runs on a **Serverless/Edge architecture**. Serverless functions are stateless, ephemeral, and terminate after a short execution timeout. 
* **Socket.io requires a persistent, stateful TCP connection** (WebSockets) to maintain client lists and broadcast messages.
* Therefore, **you cannot host a Socket.io server directly on Vercel** without connection dropping or failing.

To deploy this project, we have two primary options.

---

## 🛠 Proposed Options for Deployment

### Option 1: Split Deployment (Recommended & Easiest)
Keep our existing Socket.io codebase intact, but deploy the components to platforms optimized for them:
1. **Frontend (Vite + React)**: Deployed to **Vercel** (excellent for frontend hosting).
2. **Backend (Node.js + Socket.io)**: Deployed to a platform that supports persistent servers like **Render** or **Railway** (both have free tiers that support WebSockets).

**Required Changes**:
* Expose `SOCKET_URL` as a frontend environment variable (`import.meta.env.VITE_SOCKET_URL`) rather than hardcoding `http://localhost:5000`.
* Add a `vercel.json` configuration file in the frontend to handle client-side routing fallback.
* Host the backend on Render/Railway using a single click.

---

### Option 2: Serverless Migration (Firebase / Supabase Realtime)
Eliminate the backend Node.js server entirely and migrate the real-time logic to a serverless provider like **Supabase Realtime** or **Firebase Realtime Database**.
* The React frontend will communicate directly with Supabase/Firebase to listen for queue updates and register patients.
* This allows the **entire application** to be deployed 100% on Vercel.

**Required Changes**:
* Rewrite the state-syncing layer in `App.jsx` to use Firebase/Supabase SDKs instead of Socket.io-client.
* Delete the `backend/` directory.
* **Prerequisite**: You must provide a Supabase URL + Anon Key or a Firebase Config block.

---

## 🔌 Verification Plan

### Automated Verification
* Verify build commands for Vercel using `npm run build` locally.
* Inspect CORS configuration in the backend server.

### Manual Verification
* Deploy the frontend to Vercel and verify connection to the deployed backend.
* Test synchronization between the Vercel-hosted frontend and local/remote clients.
