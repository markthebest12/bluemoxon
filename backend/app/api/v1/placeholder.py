"""Placeholder image endpoint."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


# Simple SVG placeholder styled like a Victorian book title page
PLACEHOLDER_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="bg" patternUnits="userSpaceOnUse" width="20" height="20">
      <rect width="20" height="20" fill="#f5f0e6"/>
      <rect width="1" height="20" fill="#e8e0d0"/>
      <rect width="20" height="1" fill="#e8e0d0"/>
    </pattern>
  </defs>

  <!-- Background -->
  <rect width="300" height="400" fill="url(#bg)"/>

  <!-- Border -->
  <rect x="10" y="10" width="280" height="380" fill="none"
        stroke="#8b4513" stroke-width="3"/>
  <rect x="20" y="20" width="260" height="360" fill="none"
        stroke="#8b4513" stroke-width="1"/>

  <!-- Decorative corners -->
  <path d="M30,30 L50,30 L30,50 Z" fill="#8b4513"/>
  <path d="M270,30 L250,30 L270,50 Z" fill="#8b4513"/>
  <path d="M30,370 L50,370 L30,350 Z" fill="#8b4513"/>
  <path d="M270,370 L250,370 L270,350 Z" fill="#8b4513"/>

  <!-- Publisher mark area -->
  <rect x="100" y="120" width="100" height="100" fill="none"
        stroke="#8b4513" stroke-width="1" stroke-dasharray="5,5"/>

  <!-- Text -->
  <text x="150" y="80" text-anchor="middle" font-family="serif" font-size="14" fill="#5d4037">
    VICTORIAN
  </text>
  <text x="150" y="100" text-anchor="middle" font-family="serif" font-size="12" fill="#5d4037">
    BOOK COLLECTION
  </text>

  <text x="150" y="175" text-anchor="middle" font-family="serif" font-size="10" fill="#8b7355">
    [Image not available]
  </text>

  <!-- Publisher info -->
  <text x="150" y="280" text-anchor="middle" font-family="serif" font-size="11" fill="#5d4037">
    LONDON
  </text>
  <line x1="80" y1="290" x2="220" y2="290" stroke="#8b4513" stroke-width="1"/>
  <text x="150" y="310" text-anchor="middle" font-family="serif" font-size="10" fill="#5d4037">
    EDWARD MOXON, DOVER STREET
  </text>
  <text x="150" y="330" text-anchor="middle" font-family="serif" font-size="10" fill="#8b7355">
    MDCCCL
  </text>

  <!-- Decorative line -->
  <path d="M60,250 Q150,230 240,250" fill="none" stroke="#8b4513" stroke-width="1"/>
</svg>"""


@router.get("/placeholder")
def get_placeholder():
    """Return a Victorian-styled placeholder image."""
    return Response(
        content=PLACEHOLDER_SVG,
        media_type="image/svg+xml",
    )


@router.get("/placeholder.svg")
def get_placeholder_svg():
    """Return placeholder as SVG file."""
    return Response(
        content=PLACEHOLDER_SVG,
        media_type="image/svg+xml",
    )
