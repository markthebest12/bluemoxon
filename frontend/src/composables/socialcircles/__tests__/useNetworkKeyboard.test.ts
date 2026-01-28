// frontend/src/composables/socialcircles/__tests__/useNetworkKeyboard.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { useNetworkKeyboard, type KeyboardHandlers } from "../useNetworkKeyboard";
import { KEYBOARD_SHORTCUTS } from "@/constants/socialCircles";

describe("useNetworkKeyboard", () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    addEventListenerSpy = vi.spyOn(window, "addEventListener");
    removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
  });

  afterEach(() => {
    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });

  /**
   * Helper to create and mount a test component with keyboard handlers.
   */
  function createTestComponent(handlers: KeyboardHandlers) {
    const TestComponent = defineComponent({
      setup() {
        const result = useNetworkKeyboard(handlers);
        return { shortcuts: result.shortcuts };
      },
      template: "<div />",
    });
    return mount(TestComponent);
  }

  /**
   * Helper to dispatch a keyboard event.
   */
  function pressKey(key: string, target?: HTMLElement) {
    const event = new KeyboardEvent("keydown", {
      key,
      bubbles: true,
      cancelable: true,
    });
    if (target) {
      Object.defineProperty(event, "target", { value: target, writable: false });
    }
    window.dispatchEvent(event);
    return event;
  }

  // ==========================================================================
  // Event Registration Tests
  // ==========================================================================

  describe("event registration", () => {
    it("registers keydown listener on mount", () => {
      const wrapper = createTestComponent({});

      expect(addEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

      wrapper.unmount();
    });

    it("removes keydown listener on unmount", () => {
      const wrapper = createTestComponent({});

      wrapper.unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));
    });

    it("should not call handlers after unmount", () => {
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onEscape });

      // Verify handler works before unmount
      pressKey("Escape");
      expect(onEscape).toHaveBeenCalledTimes(1);

      // Unmount
      wrapper.unmount();

      // Key press after unmount should not trigger handler
      pressKey("Escape");
      expect(onEscape).toHaveBeenCalledTimes(1);
    });

    it("exposes shortcuts constant for help modal", () => {
      const TestComponent = defineComponent({
        setup() {
          const { shortcuts } = useNetworkKeyboard({});
          return { shortcuts };
        },
        template: "<div />",
      });

      const wrapper = mount(TestComponent);
      expect(wrapper.vm.shortcuts).toBe(KEYBOARD_SHORTCUTS);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Zoom Shortcuts Tests
  // ==========================================================================

  describe("zoom shortcuts", () => {
    it("calls onZoomIn when + is pressed", () => {
      const onZoomIn = vi.fn();
      const wrapper = createTestComponent({ onZoomIn });

      pressKey("+");

      expect(onZoomIn).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onZoomIn when = is pressed", () => {
      const onZoomIn = vi.fn();
      const wrapper = createTestComponent({ onZoomIn });

      pressKey("=");

      expect(onZoomIn).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onZoomOut when - is pressed", () => {
      const onZoomOut = vi.fn();
      const wrapper = createTestComponent({ onZoomOut });

      pressKey("-");

      expect(onZoomOut).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onZoomOut when _ is pressed", () => {
      const onZoomOut = vi.fn();
      const wrapper = createTestComponent({ onZoomOut });

      pressKey("_");

      expect(onZoomOut).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onFit when 0 is pressed", () => {
      const onFit = vi.fn();
      const wrapper = createTestComponent({ onFit });

      pressKey("0");

      expect(onFit).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Playback Shortcuts Tests
  // ==========================================================================

  describe("playback shortcuts", () => {
    it("calls onTogglePlay when Space is pressed", () => {
      const onTogglePlay = vi.fn();
      const wrapper = createTestComponent({ onTogglePlay });

      pressKey(" ");

      expect(onTogglePlay).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Navigation Shortcuts Tests
  // ==========================================================================

  describe("navigation shortcuts", () => {
    it("calls onEscape when Escape is pressed", () => {
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onEscape });

      pressKey("Escape");

      expect(onEscape).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onNextNode when ArrowRight is pressed", () => {
      const onNextNode = vi.fn();
      const wrapper = createTestComponent({ onNextNode });

      pressKey("ArrowRight");

      expect(onNextNode).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onPrevNode when ArrowLeft is pressed", () => {
      const onPrevNode = vi.fn();
      const wrapper = createTestComponent({ onPrevNode });

      pressKey("ArrowLeft");

      expect(onPrevNode).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onOpenDetails when Enter is pressed", () => {
      const onOpenDetails = vi.fn();
      const wrapper = createTestComponent({ onOpenDetails });

      pressKey("Enter");

      expect(onOpenDetails).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Action Shortcuts Tests
  // ==========================================================================

  describe("action shortcuts", () => {
    it("calls onSearch when / is pressed", () => {
      const onSearch = vi.fn();
      const wrapper = createTestComponent({ onSearch });

      pressKey("/");

      expect(onSearch).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onExport when e is pressed", () => {
      const onExport = vi.fn();
      const wrapper = createTestComponent({ onExport });

      pressKey("e");

      expect(onExport).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onShare when s is pressed", () => {
      const onShare = vi.fn();
      const wrapper = createTestComponent({ onShare });

      pressKey("s");

      expect(onShare).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });

    it("calls onHelp when ? is pressed", () => {
      const onHelp = vi.fn();
      const wrapper = createTestComponent({ onHelp });

      pressKey("?");

      expect(onHelp).toHaveBeenCalledTimes(1);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Input Focus Detection Tests
  // ==========================================================================

  describe("input focus detection", () => {
    it("ignores keyboard shortcuts when INPUT element is focused", () => {
      const onEscape = vi.fn();
      const onSearch = vi.fn();
      const wrapper = createTestComponent({ onEscape, onSearch });

      const input = document.createElement("input");
      document.body.appendChild(input);

      // Simulate key press with input as target
      pressKey("Escape", input);
      pressKey("/", input);

      expect(onEscape).not.toHaveBeenCalled();
      expect(onSearch).not.toHaveBeenCalled();

      document.body.removeChild(input);
      wrapper.unmount();
    });

    it("ignores keyboard shortcuts when TEXTAREA element is focused", () => {
      const onEscape = vi.fn();
      const onSearch = vi.fn();
      const wrapper = createTestComponent({ onEscape, onSearch });

      const textarea = document.createElement("textarea");
      document.body.appendChild(textarea);

      // Simulate key press with textarea as target
      pressKey("Escape", textarea);
      pressKey("/", textarea);

      expect(onEscape).not.toHaveBeenCalled();
      expect(onSearch).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
      wrapper.unmount();
    });

    it("processes keyboard shortcuts when DIV element is focused", () => {
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onEscape });

      const div = document.createElement("div");
      document.body.appendChild(div);

      // Simulate key press with div as target
      pressKey("Escape", div);

      expect(onEscape).toHaveBeenCalledTimes(1);

      document.body.removeChild(div);
      wrapper.unmount();
    });

    it("processes keyboard shortcuts when BUTTON element is focused", () => {
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onEscape });

      const button = document.createElement("button");
      document.body.appendChild(button);

      // Simulate key press with button as target
      pressKey("Escape", button);

      expect(onEscape).toHaveBeenCalledTimes(1);

      document.body.removeChild(button);
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Event Prevention Tests
  // ==========================================================================

  describe("event prevention", () => {
    it("prevents default on matched shortcuts", () => {
      const onZoomIn = vi.fn();
      const wrapper = createTestComponent({ onZoomIn });

      const event = new KeyboardEvent("keydown", {
        key: "+",
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      window.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
      wrapper.unmount();
    });

    it("does not prevent default for unregistered keys", () => {
      const wrapper = createTestComponent({});

      const event = new KeyboardEvent("keydown", {
        key: "x",
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      window.dispatchEvent(event);

      expect(preventDefaultSpy).not.toHaveBeenCalled();
      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Handler Registration Tests
  // ==========================================================================

  describe("handler registration", () => {
    it("does not error when handler is not provided", () => {
      const wrapper = createTestComponent({});

      // All these keys have shortcuts but no handlers registered
      expect(() => {
        pressKey("+");
        pressKey("-");
        pressKey("Escape");
        pressKey(" ");
        pressKey("/");
      }).not.toThrow();

      wrapper.unmount();
    });

    it("only calls the specific handler for each shortcut", () => {
      const onZoomIn = vi.fn();
      const onZoomOut = vi.fn();
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onZoomIn, onZoomOut, onEscape });

      pressKey("+");

      expect(onZoomIn).toHaveBeenCalledTimes(1);
      expect(onZoomOut).not.toHaveBeenCalled();
      expect(onEscape).not.toHaveBeenCalled();

      wrapper.unmount();
    });

    it("returns early after matching first shortcut", () => {
      // This tests that only one handler is called per key press
      const onZoomIn = vi.fn();
      const onZoomOut = vi.fn();
      const onFit = vi.fn();
      const wrapper = createTestComponent({ onZoomIn, onZoomOut, onFit });

      pressKey("+");
      pressKey("-");
      pressKey("0");

      expect(onZoomIn).toHaveBeenCalledTimes(1);
      expect(onZoomOut).toHaveBeenCalledTimes(1);
      expect(onFit).toHaveBeenCalledTimes(1);

      wrapper.unmount();
    });
  });

  // ==========================================================================
  // Integration Tests
  // ==========================================================================

  describe("integration", () => {
    it("handles multiple key presses in sequence", () => {
      const onZoomIn = vi.fn();
      const onZoomOut = vi.fn();
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onZoomIn, onZoomOut, onEscape });

      pressKey("+");
      pressKey("+");
      pressKey("-");
      pressKey("Escape");

      expect(onZoomIn).toHaveBeenCalledTimes(2);
      expect(onZoomOut).toHaveBeenCalledTimes(1);
      expect(onEscape).toHaveBeenCalledTimes(1);

      wrapper.unmount();
    });

    it("works with all keyboard shortcuts defined in constants", () => {
      const handlers: KeyboardHandlers = {
        onZoomIn: vi.fn(),
        onZoomOut: vi.fn(),
        onFit: vi.fn(),
        onTogglePlay: vi.fn(),
        onEscape: vi.fn(),
        onSearch: vi.fn(),
        onExport: vi.fn(),
        onShare: vi.fn(),
        onHelp: vi.fn(),
        onNextNode: vi.fn(),
        onPrevNode: vi.fn(),
        onOpenDetails: vi.fn(),
      };

      const wrapper = createTestComponent(handlers);

      // Test all shortcuts from constants
      KEYBOARD_SHORTCUTS.zoomIn.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.zoomOut.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.fitToView.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.togglePlay.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.escape.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.search.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.export.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.share.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.help.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.nextNode.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.prevNode.forEach((key) => pressKey(key));
      KEYBOARD_SHORTCUTS.openDetails.forEach((key) => pressKey(key));

      expect(handlers.onZoomIn).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.zoomIn.length);
      expect(handlers.onZoomOut).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.zoomOut.length);
      expect(handlers.onFit).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.fitToView.length);
      expect(handlers.onTogglePlay).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.togglePlay.length);
      expect(handlers.onEscape).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.escape.length);
      expect(handlers.onSearch).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.search.length);
      expect(handlers.onExport).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.export.length);
      expect(handlers.onShare).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.share.length);
      expect(handlers.onHelp).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.help.length);
      expect(handlers.onNextNode).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.nextNode.length);
      expect(handlers.onPrevNode).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.prevNode.length);
      expect(handlers.onOpenDetails).toHaveBeenCalledTimes(KEYBOARD_SHORTCUTS.openDetails.length);

      wrapper.unmount();
    });

    it("ignores keys that are not in shortcuts", () => {
      const onEscape = vi.fn();
      const wrapper = createTestComponent({ onEscape });

      // Press various keys not in shortcuts
      pressKey("a");
      pressKey("b");
      pressKey("1");
      pressKey("F1");
      pressKey("Tab");
      pressKey("Shift");

      expect(onEscape).not.toHaveBeenCalled();

      wrapper.unmount();
    });
  });
});
