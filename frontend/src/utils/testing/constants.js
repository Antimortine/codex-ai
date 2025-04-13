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

// Common test constants that can be reused across multiple test files

// Project constants
export const TEST_PROJECT_ID = 'proj-detail-123';
export const TEST_PROJECT_NAME = 'Detailed Project';
export const UPDATED_PROJECT_NAME = 'Updated Name';

// Chapter constants
export const TEST_CHAPTER_ID = 'ch-1';
export const TEST_CHAPTER_TITLE = 'The First Chapter';
export const NEW_CHAPTER_TITLE = 'New Chapter';
export const UPDATED_CHAPTER_TITLE = 'Updated Chapter';

// Character constants
export const TEST_CHARACTER_ID = 'char-1';
export const TEST_CHARACTER_NAME = 'Test Character';

// Scene constants
export const TEST_SCENE_ID = 'scene-1';
export const TEST_SCENE_TITLE = 'Test Scene';

// Note constants
export const TEST_NOTE_ID = 'note-1';
export const TEST_NOTE_TITLE = 'Test Note';

// Mock API responses
export const MOCK_PROJECT = {
  id: TEST_PROJECT_ID,
  name: TEST_PROJECT_NAME,
  description: 'A test project for unit tests',
  createdAt: '2025-01-01T12:00:00Z',
  updatedAt: '2025-01-02T12:00:00Z'
};

export const MOCK_CHAPTER = {
  id: TEST_CHAPTER_ID,
  title: TEST_CHAPTER_TITLE,
  order: 1,
  projectId: TEST_PROJECT_ID
};

export const MOCK_CHARACTER = {
  id: TEST_CHARACTER_ID,
  name: TEST_CHARACTER_NAME,
  projectId: TEST_PROJECT_ID
};
