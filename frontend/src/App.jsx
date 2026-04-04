import { useState } from 'react';

function App() {
  const [response, setResponse] = useState(null);

  const testBackend = async () => {
    try {
      // 1. grab the base url from the environment variable
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      
      // 2. attach /api/test to the end of it
      const res = await fetch(`${backendUrl}/api/test`, { method: 'POST' });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setResponse({ error: "could not connect to python backend" });
    }
  };

  return (
    <div style={{ padding: '50px' }}>
      <h2>my monorepo test</h2>
      <button onClick={testBackend} style={{ padding: '10px' }}>
        trigger python & mongodb
      </button>
      
      {response && (
        <pre style={{ marginTop: '20px', background: '#eee', padding: '10px' }}>
          {JSON.stringify(response, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default App;