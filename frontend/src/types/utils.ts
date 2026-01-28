// frontend/src/types/utils.ts

/**
 * Type utilities for TypeScript transformations.
 */

/**
 * Make all properties of T mutable (remove readonly).
 *
 * Note: This is a shallow type utility - it only removes readonly from
 * top-level properties. Nested objects retain their original readonly modifiers.
 *
 * @example
 * type Original = { readonly a: string; readonly b: { readonly c: number } };
 * type Result = Mutable<Original>;
 * // Result = { a: string; b: { readonly c: number } }
 * // Note: 'c' remains readonly
 */
export type Mutable<T> = { -readonly [P in keyof T]: T[P] };
