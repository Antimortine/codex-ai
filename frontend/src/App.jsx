/*
 * Copyright 2025 Antimortine
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Import axios for making API calls
// You might have a default CSS file like App.css or index.css imported here
import './App.css'; // Make sure this path is correct based on your project structure

function App() {
  // State variable to store the message from the backend
  const [backendMessage, setBackendMessage] = useState('Connecting to backend...');
  // State variable to store any potential error during the API call
  const [error, setError] = useState(null);

  // useEffect hook runs after the component mounts
  useEffect(() => {
    // Define an async function to fetch data
    const fetchBackendStatus = async () => {
      try {
        // Make a GET request to the backend's root endpoint
        // Ensure the URL matches where your backend is running (localhost:8000)
        const response = await axios.get('http://localhost:8000/');

        // Log the response for debugging purposes
        console.log("Backend Response:", response.data);

        // Update the state with the message from the backend response
        // We expect the backend to return { message: "..." }
        setBackendMessage(response.data.message || 'Backend responded, but no message field found.');
        setError(null); // Clear any previous errors on success
      } catch (err) {
        // Log the error for debugging
        console.error("Error fetching backend status:", err);

        // Update the error state with a helpful message
        setError(`Failed to connect to backend: ${err.message}. Check if backend is running on port 8000 and CORS is configured.`);
        setBackendMessage(''); // Clear the message on error
      }
    };

    // Call the fetch function
    fetchBackendStatus();

  }, []); // The empty dependency array [] means this effect runs only once when the component mounts

  // Render the component's UI
  return (
    <div className="App">
      <h1>Codex AI Frontend</h1>
      <hr />
      <h2>Backend Status Check:</h2>
      {/* Conditionally render the error message or the success message */}
      {error ? (
        <p style={{ color: 'red' }}><strong>Error:</strong> {error}</p>
      ) : (
        <p>Message from Backend: <strong>{backendMessage}</strong></p>
      )}
      <p><i>(If you see 'Welcome to Codex AI Backend!', the connection is working!)</i></p>
      {/* We will add routing and actual components here later */}
    </div>
  );
}

export default App;
