/**
 * Parser for AI-generated entity cross-link markers.
 *
 * Markers follow the format: {{entity:TYPE:ID|Display Name}}
 * Example: {{entity:author:32|Robert Browning}}
 */

export type TextSegment = { type: "text"; content: string };
export type LinkSegment = {
  type: "link";
  entityType: string;
  entityId: number;
  displayName: string;
};
export type Segment = TextSegment | LinkSegment;

const MARKER_RE = /\{\{entity:(\w+):(\d+)\|([^}]+)\}\}/g;

/**
 * Parse text containing entity markers into an array of segments.
 *
 * Plain text becomes TextSegment, markers become LinkSegment.
 * Malformed markers are left as plain text.
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

  return segments;
}
