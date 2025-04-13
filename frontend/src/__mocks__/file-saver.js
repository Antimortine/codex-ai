// Mock implementation of file-saver
import { vi } from 'vitest';

const FileSaver = {
  saveAs: vi.fn(),
};

export default FileSaver;
export const saveAs = vi.fn();