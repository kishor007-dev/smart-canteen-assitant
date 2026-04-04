const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

export const API_URL = isLocal
  ? "http://localhost:8000"
  : "https://smart-canteen-assitant-3.onrender.com";

export const WS_URL = isLocal
  ? "ws://localhost:8000"
  : "wss://smart-canteen-assitant-3.onrender.com";