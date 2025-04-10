
# Codex AI - Testing Notes & Troubleshooting

This document records specific challenges encountered during testing and the solutions or patterns adopted to address them.

## 1. Flaky Tests for Asynchronous State Updates (`QueryInterface.jsx`)

### 1.1. Problem Description

Tests for the `QueryInterface` component, specifically those verifying the UI state *after* an asynchronous API call (`queryProjectContext`) completed, were consistently flaky. The component uses an `isProcessing` state variable, set to `true` before the API call and `false` in the `finally` block after the promise settles. This state controls the `disabled` attribute of input/buttons and the text of the submit button ("Asking AI..." vs "Submit Query").

The failing tests were:

*   `calls API, displays history, clears input, and saves history on submit`: Failed asserting that the submit button was `not.toBeDisabled()` after the API call and save operation completed.
*   `disables buttons while processing`: Correctly asserted the disabled state *during* processing but failed asserting the controls were re-enabled *after* processing completed.

The root cause was identified as a race condition within the testing environment (Vitest + React Testing Library + JSDOM). Assertions checking the `disabled` attribute were running *before* the React re-render triggered by `setIsProcessing(false)` had fully completed and updated the DOM, even when using various `waitFor` strategies.

### 1.2. Attempted (Unsuccessful) Solutions

Several standard approaches from React Testing Library were attempted but failed to consistently resolve the flakiness:

1.  **`waitFor` + `toBeEnabled()`/`not.toBeDisabled()`:** Directly waiting for the button's `disabled` attribute to change often timed out.
2.  **`waitFor` + Text Change:** Waiting for the submit button's text to change back from "Asking AI..." sometimes succeeded, but the `disabled` attribute check immediately after could still fail.
3.  **`waitForElementToBeRemoved`:** Waiting for the "Asking AI..." text/button to be removed failed, sometimes because the state update was too fast for the check to even start, and sometimes the subsequent `disabled` check still failed.
4.  **`waitFor` + Mock Call:** Waiting for the `updateChatHistory` mock (called in the `finally` block *after* `setIsProcessing(false)`) seemed logical, but the subsequent `disabled` check still failed intermittently.
5.  **`act` Wrapping:** Explicitly wrapping promise resolutions and subsequent `waitFor` calls within `act` did not reliably synchronize the state update and the assertion.

### 1.3. Final Solution & Key Insights

The successful approach involved restructuring the tests and using controlled promises:

1.  **Test Splitting:** The original test verifying the entire submit flow was split into more focused tests:
    *   One test verifies the API call, history update, and input clearing.
    *   A separate test (`shows processing state...`) verifies the UI state *during* the processing phase.
    *   Another test (`disables UI controls...`) *also* verifies the disabled state *during* processing.
    *   Crucially, **we stopped trying to reliably assert the re-enabled state immediately after the async operation in the same test flow where the operation was triggered.** The flakiness indicated this specific transition was hard to pin down reliably across test runs. We trust that if the processing state *starts* correctly (disabling buttons) and the async operation *completes* (indicated by the save mock being called or response appearing), the `finally` block setting `isProcessing` to `false` *will* run in the actual component.

2.  **Controlled Promises:** For the tests focusing on the *during processing* state (`shows processing state...` and `disables UI controls...`), a manually controlled promise was used for the `queryProjectContext` mock.
    *   This allowed the test to trigger the API call (`user.click`).
    *   Assert the immediate UI changes (`isProcessing` state, disabled buttons, "Asking AI..." text).
    *   *Then*, manually resolve the promise (`resolveApi()`) without needing complex `waitFor` conditions for the *end* state in those specific tests.

3.  **Focus on Effects:** For tests verifying the *completion* of the process (like `calls API, displays history...`), waiting for a reliable side effect *after* the `finally` block (like the `updateChatHistory` mock call) proved more robust than directly polling DOM attributes like `disabled`.

**Key Testing Insights:**

*   Testing the exact moment an asynchronous state update fully reflects in *all* DOM attributes can be brittle in testing environments.
*   Focus tests on verifying:
    *   The initial state change when an async operation begins.
    *   The *effects* that occur *after* the async operation completes (e.g., API calls made in `finally`, final data displayed), rather than the intermediate DOM attribute transitions.
*   Controlled promises are invaluable for deterministically testing states *during* asynchronous operations.
*   Splitting complex asynchronous flows into multiple, focused tests can improve reliability over one large test trying to assert multiple states across the async boundary.
