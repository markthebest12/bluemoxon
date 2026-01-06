import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useToast } from "../useToast";

// Type assertion for dev mode (tests always run in dev)
function getToast() {
  return useToast() as ReturnType<typeof useToast> & { _reset: () => void };
}

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Reset singleton state between tests
    const toast = getToast();
    toast._reset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("should have empty toasts array", () => {
      const { toasts } = useToast();
      expect(toasts.value).toEqual([]);
    });
  });

  describe("showError", () => {
    it("should add error toast with message", () => {
      const { showError, toasts } = useToast();

      showError("Something went wrong");

      expect(toasts.value).toHaveLength(1);
      expect(toasts.value[0].type).toBe("error");
      expect(toasts.value[0].message).toBe("Something went wrong");
    });

    it("should assign unique id to each toast", () => {
      const { showError, toasts } = useToast();

      showError("Error 1");
      showError("Error 2");

      expect(toasts.value[0].id).not.toBe(toasts.value[1].id);
    });

    it("should use incrementing counter for IDs", () => {
      const { showError, toasts } = useToast();

      showError("Error 1");
      showError("Error 2");

      expect(toasts.value[0].id).toBe(1);
      expect(toasts.value[1].id).toBe(2);
    });
  });

  describe("showSuccess", () => {
    it("should add success toast with message", () => {
      const { showSuccess, toasts } = useToast();

      showSuccess("Operation completed");

      expect(toasts.value).toHaveLength(1);
      expect(toasts.value[0].type).toBe("success");
      expect(toasts.value[0].message).toBe("Operation completed");
    });
  });

  describe("auto-dismiss", () => {
    it("should remove toast after 5 seconds", async () => {
      const { showError, toasts } = useToast();

      showError("Temporary error");
      expect(toasts.value).toHaveLength(1);

      await vi.advanceTimersByTimeAsync(5000);

      expect(toasts.value).toHaveLength(0);
    });

    it("should not remove other toasts early", async () => {
      const { showError, toasts } = useToast();

      showError("First error");
      await vi.advanceTimersByTimeAsync(2000);
      showError("Second unique error");

      expect(toasts.value).toHaveLength(2);

      await vi.advanceTimersByTimeAsync(3000);
      expect(toasts.value).toHaveLength(1);
      expect(toasts.value[0].message).toBe("Second unique error");
    });
  });

  describe("dismiss", () => {
    it("should remove specific toast by id", () => {
      const { showError, dismiss, toasts } = useToast();

      showError("Error 1");
      showError("Error 2");
      const idToRemove = toasts.value[0].id;

      dismiss(idToRemove);

      expect(toasts.value).toHaveLength(1);
      expect(toasts.value[0].message).toBe("Error 2");
    });

    it("should clear timer when toast is dismissed", async () => {
      const { showError, dismiss, toasts } = useToast();

      showError("To dismiss");
      const id = toasts.value[0].id;
      dismiss(id);

      // Advance time - no errors should occur from orphaned timers
      await vi.advanceTimersByTimeAsync(10000);
      expect(toasts.value).toHaveLength(0);
    });
  });

  describe("max toasts limit", () => {
    it("should remove oldest toast when exceeding 3", () => {
      const { showError, toasts } = useToast();

      showError("Error 1");
      showError("Error 2");
      showError("Error 3");
      showError("Error 4");

      expect(toasts.value).toHaveLength(3);
      expect(toasts.value[0].message).toBe("Error 2");
      expect(toasts.value[1].message).toBe("Error 3");
      expect(toasts.value[2].message).toBe("Error 4");
    });

    it("should clear timers for shifted toasts", async () => {
      const { showError, toasts } = useToast();

      showError("Error 1");
      showError("Error 2");
      showError("Error 3");
      showError("Error 4");

      // Advance time - should not cause issues from orphaned timers
      await vi.advanceTimersByTimeAsync(10000);
      expect(toasts.value).toHaveLength(0);
    });
  });

  describe("singleton behavior", () => {
    it("should share state across multiple useToast calls", () => {
      const instance1 = useToast();
      const instance2 = useToast();

      instance1.showError("Shared error");

      expect(instance2.toasts.value).toHaveLength(1);
      expect(instance2.toasts.value[0].message).toBe("Shared error");
    });
  });

  describe("duplicate suppression", () => {
    it("should suppress duplicate messages within 2 seconds", () => {
      const { showError, toasts } = useToast();

      showError("Same error");
      showError("Same error");
      showError("Same error");

      expect(toasts.value).toHaveLength(1);
    });

    it("should allow same message after 2 seconds", async () => {
      const { showError, toasts } = useToast();

      showError("Repeated error");
      expect(toasts.value).toHaveLength(1);

      // Wait for first toast to auto-dismiss (5s) + a bit more past suppression window
      await vi.advanceTimersByTimeAsync(5001);
      expect(toasts.value).toHaveLength(0);

      // Now we can show the same message again
      showError("Repeated error");
      expect(toasts.value).toHaveLength(1);
    });

    it("should allow different messages", () => {
      const { showError, toasts } = useToast();

      showError("Error A");
      showError("Error B");
      showError("Error C");

      expect(toasts.value).toHaveLength(3);
    });
  });

  describe("pauseTimer and resumeTimer", () => {
    it("should pause auto-dismiss on hover", async () => {
      const { showError, pauseTimer, toasts } = useToast();

      showError("Hoverable error");
      const id = toasts.value[0].id;

      await vi.advanceTimersByTimeAsync(2000);
      pauseTimer(id);

      // Advance past original dismiss time
      await vi.advanceTimersByTimeAsync(5000);

      // Toast should still exist (timer was paused)
      expect(toasts.value).toHaveLength(1);
    });

    it("should resume auto-dismiss after hover ends", async () => {
      const { showError, pauseTimer, resumeTimer, toasts } = useToast();

      showError("Hoverable error");
      const id = toasts.value[0].id;

      await vi.advanceTimersByTimeAsync(2000);
      pauseTimer(id);

      await vi.advanceTimersByTimeAsync(1000);
      resumeTimer(id);

      // Should dismiss after remaining ~3 seconds
      await vi.advanceTimersByTimeAsync(3000);

      expect(toasts.value).toHaveLength(0);
    });
  });
});
