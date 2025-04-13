
# Codex AI - Frontend Testing Notes & Troubleshooting

This document outlines key strategies and solutions for writing reliable frontend tests (`vitest` + `@testing-library/react`) for the Codex AI application, particularly when dealing with asynchronous operations and state updates.

## Golden Rules for Async Frontend Tests

1.  **Prioritize Verifying Effects:** Focus assertions on the *intended side effects* of an async operation (e.g., API call made, final data displayed, prop passed to child) rather than intermediate UI states (e.g., loading spinners disappearing, buttons momentarily disabled/enabled).
2.  **Use Robust `waitFor` / `findBy*`:** When waiting for UI updates after async actions, use `findBy*` queries or `waitFor` with assertions that check for the *final, stable* state or a *direct consequence* of the completed operation. Avoid waiting for transient states.
3.  **Verify Mock API Calls First:** For tests involving user actions that trigger API calls, assert that the mock API function (`toHaveBeenCalledWith(...)`) was called correctly *before* asserting subsequent UI changes. This confirms the core action completed.
4.  **Isolate Tests:** Break down complex user flows involving multiple async steps into smaller, focused tests where possible.
5.  **Controlled Promises (for "During" State):** To test UI states *during* an async operation (e.g., loading indicators, disabled buttons), use manually controlled promises in your mocks to pause execution and assert the intermediate state.

## 1. Challenge: Flaky Tests for Async State Updates

### Problem

Tests verifying UI state immediately after asynchronous operations (API calls, timeouts) often fail due to race conditions. Assertions run before React finishes re-rendering the DOM based on the completed async task's state updates. Trying to assert intermediate states (like button enablement/disablement transitions) is particularly brittle.

### Bad Patterns (Avoid These)

```javascript
// BAD: Waiting for intermediate state (button enablement) might be flaky
await user.click(submitButton);
await waitFor(() => {
  expect(screen.getByRole('button', { name: /submit query/i })).toBeEnabled(); // Fails if re-render is slow
});
expect(mockApi.saveData).toHaveBeenCalled(); // Might run too soon

// BAD: Waiting for loading text removal is also unreliable
await user.click(submitButton);
await waitForElementToBeRemoved(() => screen.queryByText(/loading/i));
// Problem: State updates triggering other changes might not be finished yet!
expect(screen.getByText('Success!')).toBeInTheDocument(); // Might fail
```

### Good Patterns (Use These)

**Pattern 1: Verify Mock Call + Final UI State**
```javascript
// GOOD: Verify the API call first, then wait for the final expected UI
it('saves data and shows success message', async () => {
  mockApi.saveData.mockResolvedValue({ success: true });
  render(<MyComponent />);
  await user.click(screen.getByRole('button', { name: /save/i }));

  // 1. Verify the core effect (API call) happened
  await waitFor(() => {
    expect(mockApi.saveData).toHaveBeenCalledTimes(1);
    expect(mockApi.saveData).toHaveBeenCalledWith(/* expected data */);
  });

  // 2. Verify the final, stable UI outcome
  expect(await screen.findByText('Save successful!')).toBeInTheDocument(); // findBy* includes waitFor
  // Avoid asserting intermediate states like button re-enabling unless specifically testing that state.
});
```

**Pattern 2: Wait for Specific Resulting Element**
```javascript
// GOOD: Wait for an element that ONLY appears after the async operation succeeds
it('loads and displays user data', async () => {
  mockApi.fetchUser.mockResolvedValue({ data: { name: 'Alice' } });
  render(<MyComponent />);

  // Use findBy* which incorporates waitFor
  const userNameElement = await screen.findByText('User: Alice');
  expect(userNameElement).toBeInTheDocument();

  // Verify mock call *after* confirming UI update
  expect(mockApi.fetchUser).toHaveBeenCalledTimes(1);
});
```

**Pattern 3: Verify Prop Changes in Mocked Children (for Parent Components)**
```javascript
// GOOD: In parent component tests, verify props passed to mocked children
it('passes the correct activeSessionId after deletion', async () => {
  // (Setup mocks for listChatSessions, deleteChatSession)
  render(<ProjectQueryPage />);
  await waitForInitialLoad(); // Helper waits for initial stable state

  // (Simulate selecting session 1, clicking delete)

  // Wait for the *consequence* - the prop passed to the child changing
  await waitFor(() => {
    expect(lastQueryInterfaceProps.activeSessionId).toBe(SESSION_2.id);
  });

  // Verify API calls occurred
  expect(deleteChatSession).toHaveBeenCalledWith(TEST_PROJECT_ID, SESSION_1.id);
  expect(listChatSessions).toHaveBeenCalledTimes(2); // Initial + after delete
});
```


# Codex AI - Frontend Testing Notes & Troubleshooting

This document outlines key strategies and solutions for writing reliable frontend tests (`vitest` + `@testing-library/react`) for the Codex AI application, particularly when dealing with asynchronous operations and state updates.

## Golden Rules for Async Frontend Tests

1.  **Prioritize Verifying Effects:** Focus assertions on the *intended side effects* of an async operation (e.g., API call made, final data displayed, prop passed to child) rather than intermediate UI states (e.g., loading spinners disappearing, buttons momentarily disabled/enabled).
2.  **Use Robust `waitFor` / `findBy*`:** When waiting for UI updates after async actions, use `findBy*` queries or `waitFor` with assertions that check for the *final, stable* state or a *direct consequence* of the completed operation. Avoid waiting for transient states.
3.  **Verify Mock API Calls First:** For tests involving user actions that trigger API calls, assert that the mock API function (`toHaveBeenCalledWith(...)`) was called correctly *before* asserting subsequent UI changes. This confirms the core action completed.
4.  **Isolate Tests:** Break down complex user flows involving multiple async steps into smaller, focused tests where possible.
5.  **Controlled Promises (for "During" State):** To test UI states *during* an async operation (e.g., loading indicators, disabled buttons), use manually controlled promises in your mocks to pause execution and assert the intermediate state.

## 1. Challenge: Flaky Tests for Async State Updates (Simple Components)

### Problem

Tests verifying UI state immediately after asynchronous operations (API calls, timeouts) often fail due to race conditions. Assertions run before React finishes re-rendering the DOM based on the completed async task's state updates. Trying to assert intermediate states (like button enablement/disablement transitions) is particularly brittle.

### Bad Patterns (Avoid These)

```javascript
// BAD: Waiting for intermediate state (button enablement) might be flaky
await user.click(submitButton);
await waitFor(() => {
  expect(screen.getByRole('button', { name: /submit query/i })).toBeEnabled(); // Fails if re-render is slow
});
expect(mockApi.saveData).toHaveBeenCalled(); // Might run too soon

// BAD: Waiting for loading text removal is also unreliable
await user.click(submitButton);
await waitForElementToBeRemoved(() => screen.queryByText(/loading/i));
// Problem: State updates triggering other changes might not be finished yet!
expect(screen.getByText('Success!')).toBeInTheDocument(); // Might fail
```

### Good Patterns (Use These)

**Pattern 1: Verify Mock Call + Final UI State**
```javascript
// GOOD: Verify the API call first, then wait for the final expected UI
it('saves data and shows success message', async () => {
  mockApi.saveData.mockResolvedValue({ success: true });
  render(<MyComponent />);
  await user.click(screen.getByRole('button', { name: /save/i }));

  // 1. Verify the core effect (API call) happened
  await waitFor(() => {
    expect(mockApi.saveData).toHaveBeenCalledTimes(1);
    expect(mockApi.saveData).toHaveBeenCalledWith(/* expected data */);
  });

  // 2. Verify the final, stable UI outcome
  expect(await screen.findByText('Save successful!')).toBeInTheDocument(); // findBy* includes waitFor
});
```

**Pattern 2: Wait for Specific Resulting Element**
```javascript
// GOOD: Wait for an element that ONLY appears after the async operation succeeds
it('loads and displays user data', async () => {
  mockApi.fetchUser.mockResolvedValue({ data: { name: 'Alice' } });
  render(<MyComponent />);

  // Use findBy* which incorporates waitFor
  const userNameElement = await screen.findByText('User: Alice');
  expect(userNameElement).toBeInTheDocument();

  // Verify mock call *after* confirming UI update
  expect(mockApi.fetchUser).toHaveBeenCalledTimes(1);
});
```

**Pattern 3: Verify Prop Changes in Mocked Children (for Parent Components)**
```javascript
// GOOD: In parent component tests, verify props passed to mocked children
it('passes the correct activeSessionId after deletion', async () => {
  // (Setup mocks for listChatSessions, deleteChatSession)
  render(<ProjectQueryPage />);
  // Wait for initial stable state (e.g., using findBy*)
  await screen.findByRole('combobox', { name: /active session/i });

  // (Simulate selecting session 1, clicking delete)

  // Wait for the *consequence* - the prop passed to the child changing
  await waitFor(() => {
    expect(lastQueryInterfaceProps.activeSessionId).toBe(SESSION_2.id);
  });

  // Verify API calls occurred
  expect(deleteChatSession).toHaveBeenCalledWith(TEST_PROJECT_ID, SESSION_1.id);
  expect(listChatSessions).toHaveBeenCalledTimes(2); // Initial + after delete
});
```

## 2. Challenge: Complex Async Flows & Dependency Loops

### Problem

Components like ProjectQueryPage have multiple useEffect hooks fetching data and potentially triggering actions (like default session creation) which themselves trigger more fetches. Incorrect dependency arrays in useEffect or useCallback can lead to infinite loops or unexpected extra API calls, making tests fail on toHaveBeenCalledTimes assertions.

### Solution & Refinements

1.  **Stable useCallback Dependencies:** Only include variables in useCallback dependency arrays if the function's identity truly depends on them. Avoid including state setters or state variables that are only read within the function if their change shouldn't recreate the function reference.
    
2.  **Decouple Effects:** Separate concerns between useEffect hooks. For example, one effect fetches initial data, and a separate effect (potentially depending on the result of the first) handles conditional actions like creating a default item. Use useRef flags to ensure one-time actions (like default creation) don't run repeatedly.
    
3.  **Explicit State Resets:** Ensure loading/processing flags are reset reliably in finally blocks within the functions that set them to true, especially covering error paths.
    

## 3. Challenge: Persistent createRoot Errors with Complex Components

### Problem

For components with multiple concurrent asynchronous data fetches initiated in useEffect hooks on mount (like ProjectDetailPage fetching project details, chapters, characters, and scenes), tests consistently failed with createRoot(...): Target container is not a DOM element. This occurred immediately upon calling Testing Library's render, even after attempts to refine async waiting with act, flushPromises, or waitForElementToBeRemoved.

### Failed Approaches

-   **Complex renderAndWaitForLoad Helpers:** Creating a shared helper function that tried to render and then manage waiting for all initial loads proved brittle and often interfered with the test environment setup, causing the createRoot error. Wrapping render itself within act is incorrect usage.
    
-   **Insufficient waitFor:** Simply calling render and then immediately using waitFor for a single expected element wasn't enough, as other concurrent fetches and state updates might not have completed, leading to an unstable DOM state when subsequent interactions were attempted.
    

### Successful Strategy (ProjectDetailPage Example)

The key was to **remove the complex helper** and handle waiting **within each test case** after the initial render, focusing on waiting for the necessary parts of the UI to stabilize before interaction:

1.  **Simple Render:** Use a basic helper (like renderWithRouterAndParams) or render directly, ensuring necessary context providers (like Routers) are included.

```javascript
// Helper (optional, just wraps common setup)
const renderWithRouterAndParams = (ui, { initialEntries, ...options } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries || [`/projects/${TEST_PROJECT_ID}`]}>
      <Routes>
        <Route path="/projects/:projectId" element={ui} />
        {/* Other needed routes */}
      </Routes>
    </MemoryRouter>,
    options
  );
};

// In the test:
it('does something after load', async () => {
    renderWithRouterAndParams(<ProjectDetailPage />);
    // ... rest of test ...
});
```

2. **Wait for Key Elements:** Use await screen.findBy* (which includes waitFor) to wait for essential elements that indicate the initial data fetches relevant to that specific test have completed and rendered.
```javascript
it('renders project details after successful fetch', async () => {
  renderWithRouterAndParams(<ProjectDetailPage />);
  // Wait specifically for the heading that depends on getProject
  expect(await screen.findByRole('heading', { name: /project:/i })).toBeInTheDocument();
  // Now it's safe to assert other details or interact
  expect(screen.getByText(`ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();
  expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
});

it('renders chapters after successful fetch', async () => {
   listChapters.mockResolvedValue({ data: { chapters: [...] } });
   renderWithRouterAndParams(<ProjectDetailPage />);
   // Wait for the first chapter section to appear (dependent on listChapters)
   expect(await screen.findByTestId('chapter-section-ch1')).toBeInTheDocument();
   // Now it's safe to check content within it
   expect(screen.getByTestId('chapter-title-ch1')).toHaveTextContent('1: Chapter One');
});
```

3.  **Simplify Mocks (If Needed):** If a child component mock is overly complex and suspected of causing initial render issues, simplify it to return minimal JSX during debugging to isolate the problem. The final ProjectDetailPage tests worked even with a fairly detailed ChapterSection mock once the waiting strategy was corrected in the tests themselves.
    

By following these principles and adopting the refined waiting strategy, tests for complex components with multiple initial asynchronous operations become significantly more reliable and less prone to the createRoot error.

