import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// StrictMode's dev-only double-effect-invocation was fighting the video
// element's load lifecycle (see VideoStage.jsx) for no benefit toward
// tonight's demo build - dropped deliberately, not by oversight.
createRoot(document.getElementById('root')).render(<App />)
