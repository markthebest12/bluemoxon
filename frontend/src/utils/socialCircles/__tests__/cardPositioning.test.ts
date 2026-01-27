import { describe, it, expect } from 'vitest';
import { getBestCardPosition } from '../cardPositioning';

describe('getBestCardPosition', () => {
  const cardSize = { width: 280, height: 400 };
  const viewport = { width: 1200, height: 800 };

  it('places card bottom-right when node is top-left', () => {
    const nodePos = { x: 100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('bottom-right');
    expect(result.position.x).toBeGreaterThan(nodePos.x);
    expect(result.position.y).toBeGreaterThan(nodePos.y);
  });

  it('places card bottom-left when node is top-right', () => {
    const nodePos = { x: 1100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('bottom-left');
    expect(result.position.x).toBeLessThan(nodePos.x);
  });

  it('places card top-right when node is bottom-left', () => {
    const nodePos = { x: 100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('top-right');
    expect(result.position.y).toBeLessThan(nodePos.y);
  });

  it('places card top-left when node is bottom-right', () => {
    const nodePos = { x: 1100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe('top-left');
  });

  it('respects margin parameter', () => {
    const nodePos = { x: 600, y: 400 };
    const margin = 30;
    const result = getBestCardPosition(nodePos, cardSize, viewport, margin);
    const distanceX = Math.abs(result.position.x - nodePos.x);
    const distanceY = Math.abs(result.position.y - nodePos.y);
    expect(distanceX).toBeGreaterThanOrEqual(margin);
    expect(distanceY).toBeGreaterThanOrEqual(margin);
  });

  it('clamps position to viewport bounds', () => {
    const nodePos = { x: 50, y: 50 }; // Very close to edge
    const result = getBestCardPosition(nodePos, cardSize, viewport, 20);
    expect(result.position.x).toBeGreaterThanOrEqual(20);
    expect(result.position.y).toBeGreaterThanOrEqual(20);
  });
});
