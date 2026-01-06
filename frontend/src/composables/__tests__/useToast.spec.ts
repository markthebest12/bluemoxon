import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useToast } from "../useToast";

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Reset singleton state between tests
    const { _reset } = useToast();
    _reset();
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
      showError("Second error");

      expect(toasts.value).toHaveLength(2);

      await vi.advanceTimersByTimeAsync(3000);
      expect(toasts.value).toHaveLength(1);
      expect(toasts.value[0].message).toBe("Second error");
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
});
