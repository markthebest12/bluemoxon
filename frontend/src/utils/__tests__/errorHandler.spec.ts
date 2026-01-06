import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock useToast before importing errorHandler
const mockShowError = vi.fn();
const mockShowSuccess = vi.fn();

vi.mock("@/composables/useToast", () => ({
  useToast: () => ({
    showError: mockShowError,
    showSuccess: mockShowSuccess,
    toasts: { value: [] },
    dismiss: vi.fn(),
  }),
}));

// Mock console.error
const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

describe("errorHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("handleApiError", () => {
    it("should extract message from axios error", async () => {
      const { handleApiError } = await import("../errorHandler");
      const axiosError = {
        response: {
          data: {
            detail: "Book not found",
          },
        },
      };

      const result = handleApiError(axiosError, "Fetching book");

      expect(result).toBe("Book not found");
    });

    it("should fall back to Error.message", async () => {
      const { handleApiError } = await import("../errorHandler");
      const error = new Error("Network timeout");

      const result = handleApiError(error, "Connecting");

      expect(result).toBe("Network timeout");
    });

    it("should use context as fallback for unknown errors", async () => {
      const { handleApiError } = await import("../errorHandler");

      const result = handleApiError("something weird", "Loading images");

      expect(result).toBe("Failed: Loading images");
    });

    it("should call showError with extracted message", async () => {
      const { handleApiError } = await import("../errorHandler");
      const error = new Error("Server error");

      handleApiError(error, "Saving");

      expect(mockShowError).toHaveBeenCalledWith("Server error");
    });

    it("should log error to console with context", async () => {
      const { handleApiError } = await import("../errorHandler");
      const error = new Error("Database error");

      handleApiError(error, "Querying");

      expect(consoleErrorSpy).toHaveBeenCalledWith("[Querying]", "Database error", error);
    });

    it("should return the extracted message", async () => {
      const { handleApiError } = await import("../errorHandler");
      const error = new Error("Test error");

      const result = handleApiError(error, "Testing");

      expect(result).toBe("Test error");
    });
  });

  describe("handleSuccess", () => {
    it("should call showSuccess with message", async () => {
      const { handleSuccess } = await import("../errorHandler");

      handleSuccess("Item deleted");

      expect(mockShowSuccess).toHaveBeenCalledWith("Item deleted");
    });
  });

  describe("integration with existing error utils", () => {
    it("should handle axios error with nested detail", async () => {
      const { handleApiError } = await import("../errorHandler");
      const axiosError = {
        response: {
          data: {
            detail: "Validation failed: email is required",
          },
        },
        message: "Request failed with status 400",
      };

      const result = handleApiError(axiosError, "Form submission");

      expect(result).toBe("Validation failed: email is required");
      expect(mockShowError).toHaveBeenCalledWith("Validation failed: email is required");
    });

    it("should handle error without response", async () => {
      const { handleApiError } = await import("../errorHandler");
      // Real axios network errors are Error instances
      const networkError = new Error("Network Error");

      const result = handleApiError(networkError, "API call");

      expect(result).toBe("Network Error");
    });
  });
});
