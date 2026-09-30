import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ShareView from "./components/ShareView.jsx";
import "leaflet/dist/leaflet.css";
import "./index.css";

// No router dependency needed for a single public route: /share/{locationId}
// renders the read-only community alert page, everything else renders the
// full responder dashboard.
const shareMatch = window.location.pathname.match(/^\/share\/(.+)$/);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {shareMatch ? <ShareView locationId={decodeURIComponent(shareMatch[1])} /> : <App />}
  </React.StrictMode>
);
