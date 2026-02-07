/**
 * Parser for AI-generated entity cross-link markers.
 *
 * Canonical format: {{entity:TYPE:ID|Display Name}}
 * Example: {{entity:author:32|Robert Browning}}
 *
 * Also handles malformed variants the AI sometimes produces:
 * - {{TYPE:ID|Name}}       — missing entity: prefix, resolved as link
 * - {{entity:TYPE|Name}}   — missing ID, stripped to plain text
 * - {{Name}}               — bare name, stripped to plain text
 */

export type TextSegment = { type: "text"; content: string };
export type LinkSegment = {
  type: "link";
  entityType: string;
  entityId: number;
  displayName: string;
};
export type Segment = TextSegment | LinkSegment;

/** Matches {{entity:TYPE:ID|Name}} and {{TYPE:ID|Name}} (entity: prefix optional). */
const MARKER_RE = /\{\{(?:entity:)?(\w+):(\d+)\|([^}]+)\}\}/g;

/** Matches any remaining {{...}} patterns after the primary pass. */
const LEFTOVER_RE = /\{\{([^}]+)\}\}/g;

/** Matches unwrapped entity references: entity:TYPE:Name (no braces, no ID). */
const UNWRAPPED_RE =
  /entity:\w+:([A-Z][a-zA-Z''-]*(?:\s+(?:(?:and|of|the|de|von|van)\s+)?[A-Z][a-zA-Z''-]*)*)/g;

/**
 * Extract a display name from the inner content of a leftover {{...}} marker.
 * If the content contains `|`, return the text after the last `|`.
 * Otherwise return the full content.
 */
function extractDisplayName(inner: string): string {
  const pipeIndex = inner.lastIndexOf("|");
  return pipeIndex >= 0 ? inner.slice(pipeIndex + 1) : inner;
}

/**
 * Second-pass helper: scan text segments for leftover `{{...}}` patterns
 * and replace them with their extracted display name as plain text.
 */
function stripRemainingMarkers(segments: Segment[]): Segment[] {
  const result: Segment[] = [];

  for (const segment of segments) {
    if (segment.type !== "text") {
      result.push(segment);
      continue;
    }

    const text = segment.content;
    let lastIndex = 0;
    let hasLeftover = false;

    for (const match of text.matchAll(LEFTOVER_RE)) {
      hasLeftover = true;
      const matchStart = match.index!;

      if (matchStart > lastIndex) {
        result.push({ type: "text", content: text.slice(lastIndex, matchStart) });
      }

      result.push({ type: "text", content: extractDisplayName(match[1]) });
      lastIndex = matchStart + match[0].length;
    }

    if (!hasLeftover) {
      result.push(segment);
    } else if (lastIndex < text.length) {
      result.push({ type: "text", content: text.slice(lastIndex) });
    }
  }

  return result;
}

/**
 * Third-pass helper: strip unwrapped `entity:TYPE:Name` patterns
 * that the AI sometimes produces without braces.
 */
function stripUnwrappedMarkers(segments: Segment[]): Segment[] {
  const result: Segment[] = [];

  for (const segment of segments) {
    if (segment.type !== "text") {
      result.push(segment);
      continue;
    }

    const text = segment.content;
    let lastIndex = 0;
    let hasMatch = false;

    for (const match of text.matchAll(UNWRAPPED_RE)) {
      hasMatch = true;
      const matchStart = match.index!;

      if (matchStart > lastIndex) {
        result.push({ type: "text", content: text.slice(lastIndex, matchStart) });
      }

      result.push({ type: "text", content: match[1] });
      lastIndex = matchStart + match[0].length;
    }

    if (!hasMatch) {
      result.push(segment);
    } else if (lastIndex < text.length) {
      result.push({ type: "text", content: text.slice(lastIndex) });
    }
  }

  return result;
}

/**
 * Parse text containing entity markers into an array of segments.
 *
 * Plain text becomes TextSegment, well-formed markers become LinkSegment.
 * Malformed markers are stripped to their display name as plain text.
 */
export function parseEntityMarkers(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(MARKER_RE)) {
    const matchStart = match.index!;

    // Add text before this marker (if any)
    if (matchStart > lastIndex) {
      segments.push({
        type: "text",
        content: text.slice(lastIndex, matchStart),
      });
    }

    segments.push({
      type: "link",
      entityType: match[1],
      entityId: parseInt(match[2], 10),
      displayName: match[3],
    });

    lastIndex = matchStart + match[0].length;
  }

  // Add remaining text after last marker
  if (lastIndex <= text.length) {
    const remaining = text.slice(lastIndex);
    if (remaining || segments.length === 0) {
      segments.push({ type: "text", content: remaining });
    }
  }

  // Second pass: strip any leftover {{...}} patterns from text segments
  const afterBraces = stripRemainingMarkers(segments);

  // Third pass: strip unwrapped entity:TYPE:Name patterns from text segments
  return stripUnwrappedMarkers(afterBraces);
}
