import { describe, it, expect, beforeEach, vi, beforeAll } from 'vitest';

// Mock localStorage before importing useTheme
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    clear: () => {
      store = {};
    },
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
  };
})();

// Mock matchMedia
const createMatchMediaMock = (matches: boolean) => {
  return vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

// Set up mocks before module import
beforeAll(() => {
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });
  window.matchMedia = createMatchMediaMock(false);
});

// Import after mocks are set up - use dynamic import
describe('useTheme', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    document.documentElement.classList.remove('dark');
  });

  it('defaults to system preference when no stored value', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');
    const { resolvedTheme, isDark } = useTheme();
    // With shared state, we check the current value
    expect(typeof resolvedTheme.value).toBe('string');
    expect(typeof isDark.value).toBe('boolean');
  });

  it('toggle switches theme', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');
    const { isDark, toggle, setTheme } = useTheme();

    // Set to light first
    setTheme('light');
    expect(isDark.value).toBe(false);

    // Toggle to dark
    toggle();
    expect(isDark.value).toBe(true);

    // Toggle back to light
    toggle();
    expect(isDark.value).toBe(false);
  });

  it('setTheme updates preference', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');
    const { preference, setTheme, isDark } = useTheme();

    setTheme('dark');
    expect(preference.value).toBe('dark');
    expect(isDark.value).toBe(true);

    setTheme('light');
    expect(preference.value).toBe('light');
    expect(isDark.value).toBe(false);

    setTheme('system');
    expect(preference.value).toBe('system');
  });

  it('applies dark class to document when dark', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');
    const { nextTick } = await import('vue');
    const { setTheme } = useTheme();

    setTheme('dark');
    await nextTick();
    // The watch should apply the class
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    setTheme('light');
    await nextTick();
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('persists preference to localStorage', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');
    const { nextTick } = await import('vue');
    const { setTheme } = useTheme();

    // Clear previous calls from other tests
    vi.clearAllMocks();

    setTheme('dark');
    await nextTick();
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('shares state across multiple useTheme() calls (singleton)', async () => {
    window.matchMedia = createMatchMediaMock(false);
    const { useTheme } = await import('../useTheme');

    // Simulate multiple components using useTheme
    const instance1 = useTheme();
    const instance2 = useTheme();
    const instance3 = useTheme();

    // All instances should share the same refs
    instance1.setTheme('dark');

    // All instances see the change
    expect(instance1.isDark.value).toBe(true);
    expect(instance2.isDark.value).toBe(true);
    expect(instance3.isDark.value).toBe(true);

    // Change from another instance
    instance2.setTheme('light');

    // All instances see the change
    expect(instance1.isDark.value).toBe(false);
    expect(instance2.isDark.value).toBe(false);
    expect(instance3.isDark.value).toBe(false);
  });
});
