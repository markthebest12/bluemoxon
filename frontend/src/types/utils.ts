// frontend/src/types/utils.ts

/**
 * Type utilities for TypeScript transformations.
 */

/** Make all properties of T mutable (remove readonly) */
export type Mutable<T> = { -readonly [P in keyof T]: T[P] };
