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

import React from 'react';
import { Outlet, Link } from 'react-router-dom'; // Outlet renders nested routes

function MainLayout() {
  return (
    <div>
      <header style={{ padding: '1rem', backgroundColor: '#eee' }}>
        <nav>
          <Link to="/" style={{ marginRight: '1rem' }}>Home (Project List)</Link>
          {/* Add other global navigation links here later */}
        </nav>
      </header>
      <main style={{ padding: '1rem' }}>
        <Outlet /> {/* Child routes will render here */}
      </main>
      <footer style={{ padding: '1rem', marginTop: '2rem', backgroundColor: '#eee', textAlign: 'center' }}>
        Codex AI - Footer
      </footer>
    </div>
  );
}

export default MainLayout;