import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import ImageGallerySection from "../ImageGallerySection.vue";
import type { BookImage } from "@/types/books";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock error handler utils
vi.mock("@/utils/errorHandler", () => ({
  handleApiError: vi.fn(),
  handleSuccess: vi.fn(),
}));

describe("ImageGallerySection", () => {
  const mockImages: BookImage[] = [
    {
      id: 1,
      url: "https://example.com/image1.jpg",
      thumbnail_url: "https://example.com/thumb1.jpg",
      image_type: "photo",
      caption: "Front cover",
      display_order: 0,
      is_primary: true,
    },
    {
      id: 2,
      url: "https://example.com/image2.jpg",
      thumbnail_url: "https://example.com/thumb2.jpg",
      image_type: "photo",
      caption: "Back cover",
      display_order: 1,
      is_primary: false,
    },
    {
      id: 3,
      url: "https://example.com/image3.jpg",
      thumbnail_url: "https://example.com/thumb3.jpg",
      image_type: "photo",
      caption: null,
      display_order: 2,
      is_primary: false,
    },
  ];

  const defaultProps = {
    bookId: 123,
    images: mockImages,
    isEditor: true,
  };

  const mountOptions = {
    global: {
      stubs: {
        BookThumbnail: true,
        ImageUploadModal: true,
        ImageReorderModal: true,
        Teleport: true,
      },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders image grid with correct number of images", () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Find all image elements in the grid
    const images = wrapper.findAll("img");
    expect(images.length).toBe(mockImages.length);
  });

  it('clicking image thumbnail emits "open-carousel" with correct index', async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Find the clickable image buttons (not delete buttons) and click the second one (index 1)
    // The image buttons contain <img> elements, delete buttons contain SVG with trash icon
    const imageButtons = wrapper.findAll(".grid > div > button.w-full");
    expect(imageButtons.length).toBe(mockImages.length);

    await imageButtons[1].trigger("click");

    const emitted = wrapper.emitted("open-carousel");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual([1]);
  });

  it('shows "Add Images" button for editors only', () => {
    // Test with editor
    const wrapperEditor = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });
    expect(wrapperEditor.text()).toContain("Add Images");

    // Test without editor
    const wrapperNonEditor = mount(ImageGallerySection, {
      props: {
        ...defaultProps,
        isEditor: false,
      },
      ...mountOptions,
    });
    expect(wrapperNonEditor.text()).not.toContain("Add Images");
  });

  it('shows "Reorder" button when images.length > 1 and isEditor', () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    expect(wrapper.text()).toContain("Reorder");
  });

  it('hides "Reorder" button when only 1 image', () => {
    const wrapper = mount(ImageGallerySection, {
      props: {
        ...defaultProps,
        images: [mockImages[0]],
      },
      ...mountOptions,
    });

    expect(wrapper.text()).not.toContain("Reorder");
  });

  it('hides "Reorder" button for non-editors', () => {
    const wrapper = mount(ImageGallerySection, {
      props: {
        ...defaultProps,
        isEditor: false,
      },
      ...mountOptions,
    });

    expect(wrapper.text()).not.toContain("Reorder");
  });

  it("shows delete button on image hover for editors", () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Find delete buttons (they have title="Delete image")
    const deleteButtons = wrapper.findAll('button[title="Delete image"]');
    expect(deleteButtons.length).toBe(mockImages.length);
  });

  it("does not show delete button for non-editors", () => {
    const wrapper = mount(ImageGallerySection, {
      props: {
        ...defaultProps,
        isEditor: false,
      },
      ...mountOptions,
    });

    const deleteButtons = wrapper.findAll('button[title="Delete image"]');
    expect(deleteButtons.length).toBe(0);
  });

  it("clicking delete opens confirmation modal", async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Initially modal should not be visible
    expect(wrapper.text()).not.toContain("Delete Image");

    // Click delete button on first image
    const deleteButton = wrapper.find('button[title="Delete image"]');
    await deleteButton.trigger("click");

    // Modal should now be visible
    expect(wrapper.text()).toContain("Delete Image");
    expect(wrapper.text()).toContain("Are you sure you want to delete this image?");
  });

  it("shows empty state with BookThumbnail when no images", () => {
    const wrapper = mount(ImageGallerySection, {
      props: {
        ...defaultProps,
        images: [],
      },
      ...mountOptions,
    });

    // Check for BookThumbnail stub
    expect(wrapper.findComponent({ name: "BookThumbnail" }).exists()).toBe(true);
    expect(wrapper.text()).toContain("No images available");
  });

  it('upload modal opens when "Add Images" clicked', async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Find the Add Images button
    const addButton = wrapper.findAll("button").find((btn) => btn.text().includes("Add Images"));
    expect(addButton).toBeDefined();

    await addButton!.trigger("click");

    // Find the ImageUploadModal and check its visible prop
    const uploadModal = wrapper.findComponent({ name: "ImageUploadModal" });
    expect(uploadModal.exists()).toBe(true);
    expect(uploadModal.props("visible")).toBe(true);
  });

  it('reorder modal opens when "Reorder" clicked', async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Find the Reorder button
    const reorderButton = wrapper.findAll("button").find((btn) => btn.text().includes("Reorder"));
    expect(reorderButton).toBeDefined();

    await reorderButton!.trigger("click");

    // Find the ImageReorderModal and check its visible prop
    const reorderModal = wrapper.findComponent({ name: "ImageReorderModal" });
    expect(reorderModal.exists()).toBe(true);
    expect(reorderModal.props("visible")).toBe(true);
  });

  it("renders the Images heading", () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    expect(wrapper.find("h2").text()).toBe("Images");
  });

  it("displays image captions as alt text", () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    const images = wrapper.findAll("img");
    expect(images[0].attributes("alt")).toBe("Front cover");
    expect(images[1].attributes("alt")).toBe("Back cover");
    expect(images[2].attributes("alt")).toBe("Image 3"); // Fallback for null caption
  });

  it("uses correct thumbnail URLs for images", () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    const images = wrapper.findAll("img");
    expect(images[0].attributes("src")).toBe("https://example.com/thumb1.jpg");
    expect(images[1].attributes("src")).toBe("https://example.com/thumb2.jpg");
  });

  it("emits open-carousel with index 0 when first image clicked", async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    const imageButtons = wrapper.findAll(".grid > div > button.w-full");
    await imageButtons[0].trigger("click");

    const emitted = wrapper.emitted("open-carousel");
    expect(emitted).toBeTruthy();
    expect(emitted![0]).toEqual([0]);
  });

  it("cancel button closes delete modal", async () => {
    const wrapper = mount(ImageGallerySection, {
      props: defaultProps,
      ...mountOptions,
    });

    // Open delete modal
    const deleteButton = wrapper.find('button[title="Delete image"]');
    await deleteButton.trigger("click");
    expect(wrapper.text()).toContain("Delete Image");

    // Find and click Cancel button
    const cancelButton = wrapper.findAll("button").find((btn) => btn.text() === "Cancel");
    expect(cancelButton).toBeDefined();
    await cancelButton!.trigger("click");

    // Modal should be closed
    expect(wrapper.text()).not.toContain("Are you sure you want to delete this image?");
  });
});
