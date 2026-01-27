export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export type Quadrant = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

interface QuadrantSpace {
  width: number;
  height: number;
}

interface PositionResult {
  position: Position;
  quadrant: Quadrant;
}

export function getBestCardPosition(
  nodePos: Position,
  cardSize: Size,
  viewport: Size,
  margin: number = 20
): PositionResult {
  const quadrants: Record<Quadrant, QuadrantSpace> = {
    'top-left': {
      width: nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'top-right': {
      width: viewport.width - nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'bottom-left': {
      width: nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
    'bottom-right': {
      width: viewport.width - nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
  };

  const scores = (Object.entries(quadrants) as [Quadrant, QuadrantSpace][]).map(
    ([name, space]) => {
      const canFit = space.width >= cardSize.width && space.height >= cardSize.height;
      if (!canFit) return { name, score: -1 };

      let score = 0;
      score += Math.min(space.width - cardSize.width, 100);
      score += Math.min(space.height - cardSize.height, 100);
      if (name.includes('right')) score += 20;
      if (name.includes('bottom')) score += 10;

      return { name, score };
    }
  );

  const best = scores.reduce((a, b) => (a.score > b.score ? a : b));
  const quadrant: Quadrant = best.score >= 0 ? best.name : 'bottom-right';

  const position: Position = {
    x: quadrant.includes('right')
      ? nodePos.x + margin
      : nodePos.x - cardSize.width - margin,
    y: quadrant.includes('bottom')
      ? nodePos.y + margin
      : nodePos.y - cardSize.height - margin,
  };

  position.x = Math.max(margin, Math.min(position.x, viewport.width - cardSize.width - margin));
  position.y = Math.max(margin, Math.min(position.y, viewport.height - cardSize.height - margin));

  return { position, quadrant };
}
