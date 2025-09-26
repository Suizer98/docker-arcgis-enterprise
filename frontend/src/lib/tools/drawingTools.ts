import { tool } from 'ai';
import { z } from 'zod';
import { mapController } from '../Map/mapController';

// Helper function to parse and validate colors
function parseColor(colorInput: string): string {
  if (!colorInput) return 'red';

  const color = colorInput.toLowerCase().trim();

  // Handle common color variations
  const colorMap: { [key: string]: string } = {
    red: '#FF0000',
    blue: '#0000FF',
    green: '#00FF00',
    yellow: '#FFFF00',
    orange: '#FFA500',
    purple: '#800080',
    pink: '#FFC0CB',
    brown: '#A52A2A',
    black: '#000000',
    white: '#FFFFFF',
    gray: '#808080',
    grey: '#808080',
    cyan: '#00FFFF',
    magenta: '#FF00FF',
    lime: '#00FF00',
    navy: '#000080',
    maroon: '#800000',
    olive: '#808000',
    teal: '#008080',
    silver: '#C0C0C0',
    gold: '#FFD700',
    crimson: '#DC143C',
    darkred: '#8B0000',
    lightblue: '#ADD8E6',
    darkblue: '#00008B',
    lightgreen: '#90EE90',
    darkgreen: '#006400',
  };

  // If it's a mapped color, return the hex value
  if (colorMap[color]) {
    return colorMap[color];
  }

  // If it's already a hex color, return as is
  if (color.startsWith('#') && /^#[0-9A-Fa-f]{6}$/.test(color)) {
    return color.toUpperCase();
  }

  // If it's an RGB format, convert to hex
  if (color.startsWith('rgb(') && color.endsWith(')')) {
    const rgb = color
      .slice(4, -1)
      .split(',')
      .map(n => parseInt(n.trim()));
    if (rgb.length === 3 && rgb.every(n => n >= 0 && n <= 255)) {
      return `#${rgb
        .map(n => n.toString(16).padStart(2, '0'))
        .join('')
        .toUpperCase()}`;
    }
  }

  // Default to red if color is not recognized
  return '#FF0000';
}

// Draw line tool
export const drawLineTool = tool({
  description: 'Draw a line between two points on the map',
  inputSchema: z.object({
    startLatitude: z
      .number()
      .min(-90)
      .max(90)
      .describe('The starting latitude coordinate'),
    startLongitude: z
      .number()
      .min(-180)
      .max(180)
      .describe('The starting longitude coordinate'),
    endLatitude: z
      .number()
      .min(-90)
      .max(90)
      .describe('The ending latitude coordinate'),
    endLongitude: z
      .number()
      .min(-180)
      .max(180)
      .describe('The ending longitude coordinate'),
    color: z
      .string()
      .optional()
      .describe(
        'Optional: Color of the line (supports: color names like "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white", "gray", "cyan", "magenta", "lime", "navy", "maroon", "olive", "teal", "silver", "gold", "crimson", "darkred", "lightblue", "darkblue", "lightgreen", "darkgreen", or hex codes like "#FF0000", or RGB like "rgb(255,0,0)")'
      ),
  }),
  execute: async ({
    startLatitude,
    startLongitude,
    endLatitude,
    endLongitude,
    color = 'red',
  }) => {
    try {
      const parsedColor = parseColor(color);

      // Actually draw the line on the map
      const result = await mapController.drawLine(
        startLatitude,
        startLongitude,
        endLatitude,
        endLongitude,
        parsedColor
      );

      if (result.success) {
        return {
          success: true,
          message: `Line drawn from (${startLatitude.toFixed(4)}, ${startLongitude.toFixed(4)}) to (${endLatitude.toFixed(4)}, ${endLongitude.toFixed(4)}) in ${parsedColor}`,
          coordinates: {
            start: { lat: startLatitude, lng: startLongitude },
            end: { lat: endLatitude, lng: endLongitude },
          },
          color: parsedColor,
          originalColor: color,
          type: 'line',
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to draw line on map',
          error: 'Map drawing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw line',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw point/marker tool
export const drawPointTool = tool({
  description: 'Draw a point or marker on the map with customizable appearance',
  inputSchema: z.object({
    latitude: z.number().min(-90).max(90).describe('The latitude coordinate'),
    longitude: z
      .number()
      .min(-180)
      .max(180)
      .describe('The longitude coordinate'),
    color: z
      .string()
      .optional()
      .describe(
        'Optional: Outline color of the point (supports: color names like "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white", "gray", "cyan", "magenta", "lime", "navy", "maroon", "olive", "teal", "silver", "gold", "crimson", "darkred", "lightblue", "darkblue", "lightgreen", "darkgreen", or hex codes like "#FF0000", or RGB like "rgb(255,0,0)")'
      ),
    size: z
      .number()
      .optional()
      .describe('Optional: Size of the point in pixels'),
    label: z.string().optional().describe('Optional: Label text for the point'),
    fillColor: z
      .string()
      .optional()
      .describe('Optional: Fill color of the point (leave empty for no fill)'),
    outlineColor: z
      .string()
      .optional()
      .describe('Optional: Outline color of the point (default: black)'),
    outlineWidth: z
      .number()
      .optional()
      .describe('Optional: Width of the outline in pixels (default: 1)'),
    opacity: z
      .number()
      .min(0)
      .max(1)
      .optional()
      .describe('Optional: Opacity of the point (0-1, default: 1)'),
    filled: z
      .boolean()
      .optional()
      .describe('Optional: Whether the point should be filled (default: true)'),
  }),
  execute: async ({
    latitude,
    longitude,
    color = 'red',
    size = 10,
    label,
    fillColor,
    outlineColor,
    outlineWidth,
    opacity,
    filled = true,
  }) => {
    try {
      const parsedColor = parseColor(color);
      const parsedFillColor = fillColor ? parseColor(fillColor) : null;
      const parsedOutlineColor = outlineColor ? parseColor(outlineColor) : null;

      // Actually draw the point on the map
      const result = await mapController.drawPoint(
        latitude,
        longitude,
        parsedColor,
        size,
        label,
        'points',
        parsedFillColor || undefined,
        parsedOutlineColor || undefined,
        outlineWidth,
        opacity,
        filled
      );

      if (result.success) {
        let message = `Point drawn at (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
        if (filled && parsedFillColor) {
          message += ` with ${parsedFillColor} fill`;
        }
        if (parsedOutlineColor) {
          message += ` and ${parsedOutlineColor} outline`;
        } else {
          message += ` in ${parsedColor}`;
        }
        if (label) {
          message += ` with label "${label}"`;
        }

        return {
          success: true,
          message,
          coordinates: { lat: latitude, lng: longitude },
          color: parsedColor,
          size: size,
          label: label,
          type: 'point',
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to draw point on map',
          error: 'Map drawing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw point',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw rectangle tool
export const drawRectangleTool = tool({
  description:
    'Draw a rectangle on the map using southwest and northeast corner coordinates (NOT center, rows, columns, or cellSize)',
  inputSchema: z.object({
    southwest: z.object({
      latitude: z
        .number()
        .describe('Southwest corner latitude (required for rectangles)'),
      longitude: z
        .number()
        .describe('Southwest corner longitude (required for rectangles)'),
    }),
    northeast: z.object({
      latitude: z
        .number()
        .describe('Northeast corner latitude (required for rectangles)'),
      longitude: z
        .number()
        .describe('Northeast corner longitude (required for rectangles)'),
    }),
    color: z.string().optional().describe('Color of the rectangle border'),
    fillColor: z.string().optional().describe('Fill color of the rectangle'),
    opacity: z
      .number()
      .min(0)
      .max(1)
      .optional()
      .describe('Opacity of the rectangle (0-1)'),
  }),
  execute: async ({
    southwest,
    northeast,
    color = 'red',
    fillColor,
    opacity = 0.3,
  }) => {
    try {
      const borderColor = parseColor(color);
      const fill = fillColor ? parseColor(fillColor) : borderColor;

      const result = await mapController.drawRectangle({
        southwest: [southwest.longitude, southwest.latitude],
        northeast: [northeast.longitude, northeast.latitude],
        color: borderColor,
        fillColor: fill,
        opacity: opacity,
      });

      if (result.success) {
        return {
          success: true,
          message: `Rectangle drawn from (${southwest.latitude.toFixed(4)}, ${southwest.longitude.toFixed(4)}) to (${northeast.latitude.toFixed(4)}, ${northeast.longitude.toFixed(4)})`,
          type: 'rectangle',
          coordinates: { southwest, northeast },
          color: borderColor,
          fillColor: fill,
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to draw rectangle',
          error: 'Rectangle drawing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw rectangle',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw polygon tool
export const drawPolygonTool = tool({
  description: 'Draw a polygon on the map with specified vertices',
  inputSchema: z.object({
    vertices: z
      .array(
        z.object({
          latitude: z.number().describe('Vertex latitude'),
          longitude: z.number().describe('Vertex longitude'),
        })
      )
      .min(3)
      .describe('Array of polygon vertices (minimum 3 points)'),
    color: z.string().optional().describe('Color of the polygon border'),
    fillColor: z.string().optional().describe('Fill color of the polygon'),
    opacity: z
      .number()
      .min(0)
      .max(1)
      .optional()
      .describe('Opacity of the polygon (0-1)'),
  }),
  execute: async ({ vertices, color = 'red', fillColor, opacity = 0.3 }) => {
    try {
      const borderColor = parseColor(color);
      const fill = fillColor ? parseColor(fillColor) : borderColor;

      const result = await mapController.drawPolygon({
        vertices: vertices.map(v => [v.longitude, v.latitude]),
        color: borderColor,
        fillColor: fill,
        opacity: opacity,
      });

      if (result.success) {
        return {
          success: true,
          message: `Polygon drawn with ${vertices.length} vertices`,
          type: 'polygon',
          coordinates: vertices,
          color: borderColor,
          fillColor: fill,
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to draw polygon',
          error: 'Polygon drawing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw polygon',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw circle tool
export const drawCircleTool = tool({
  description:
    'Draw a circle on the map with specified center point and radius (NOT for rectangles or grids)',
  inputSchema: z.object({
    center: z.object({
      latitude: z.number().describe('Latitude of the circle center'),
      longitude: z.number().describe('Longitude of the circle center'),
    }),
    radius: z
      .number()
      .min(0.01)
      .max(1000)
      .describe('Radius of the circle in kilometers'),
    color: z
      .string()
      .optional()
      .describe('Color of the circle border (e.g., "red", "blue", "#FF0000")'),
    fillColor: z
      .string()
      .optional()
      .describe(
        'Fill color of the circle (e.g., "red", "blue", "#FF0000"). Leave empty for no fill'
      ),
    opacity: z
      .number()
      .min(0)
      .max(1)
      .optional()
      .describe('Opacity of the circle (0-1)'),
    filled: z
      .boolean()
      .optional()
      .describe('Whether the circle should be filled (default: false)'),
  }),
  execute: async ({
    center,
    radius,
    color = 'red',
    fillColor,
    opacity = 0.3,
    filled = false,
  }) => {
    try {
      // Parse colors
      const borderColor = parseColor(color);
      const fill = filled && fillColor ? parseColor(fillColor) : null;

      // Draw circle on the map
      const result = await mapController.drawCircle({
        center: [center.longitude, center.latitude],
        radius: radius * 1000, // Convert km to meters
        color: borderColor,
        fillColor: fill,
        opacity: opacity,
        filled: filled,
      });

      if (result.success) {
        return {
          success: true,
          message: `Circle drawn at (${center.latitude.toFixed(4)}, ${center.longitude.toFixed(4)}) with radius ${radius}km`,
          type: 'circle',
          coordinates: center,
          radius: radius,
          color: borderColor,
          fillColor: fill,
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to draw circle',
          error: 'Circle drawing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw circle',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw arrow tool (line with arrowhead)
export const drawArrowTool = tool({
  description: 'Draw an arrow on the map pointing from one location to another',
  inputSchema: z.object({
    start: z.object({
      latitude: z.number().describe('Start point latitude'),
      longitude: z.number().describe('Start point longitude'),
    }),
    end: z.object({
      latitude: z.number().describe('End point latitude'),
      longitude: z.number().describe('End point longitude'),
    }),
    color: z.string().optional().describe('Color of the arrow'),
    size: z.number().min(1).max(50).optional().describe('Size of the arrow'),
  }),
  execute: async ({ start, end, color = 'red', size = 10 }) => {
    try {
      const borderColor = parseColor(color);

      // Draw the main line
      const lineResult = await mapController.drawLine(
        start.latitude,
        start.longitude,
        end.latitude,
        end.longitude,
        borderColor
      );

      if (!lineResult.success) {
        return {
          success: false,
          message: 'Failed to draw arrow line',
          error: lineResult.message,
        };
      }

      // Calculate arrowhead direction
      const dx = end.longitude - start.longitude;
      const dy = end.latitude - start.latitude;
      const length = Math.sqrt(dx * dx + dy * dy);
      const unitX = dx / length;
      const unitY = dy / length;

      // Calculate arrowhead points
      const arrowLength = 0.001 * (size / 10); // Scale with size
      const arrowAngle = Math.PI / 6; // 30 degrees

      const arrowX1 =
        end.longitude -
        arrowLength *
          (unitX * Math.cos(arrowAngle) + unitY * Math.sin(arrowAngle));
      const arrowY1 =
        end.latitude -
        arrowLength *
          (unitY * Math.cos(arrowAngle) - unitX * Math.sin(arrowAngle));
      const arrowX2 =
        end.longitude -
        arrowLength *
          (unitX * Math.cos(-arrowAngle) + unitY * Math.sin(-arrowAngle));
      const arrowY2 =
        end.latitude -
        arrowLength *
          (unitY * Math.cos(-arrowAngle) - unitX * Math.sin(-arrowAngle));

      // Draw arrowhead as a small triangle
      const arrowResult = await mapController.drawPolygon({
        vertices: [
          [end.longitude, end.latitude],
          [arrowX1, arrowY1],
          [arrowX2, arrowY2],
          [end.longitude, end.latitude],
        ],
        color: borderColor,
        fillColor: borderColor,
        opacity: 1,
      });

      if (arrowResult.success) {
        return {
          success: true,
          message: `Arrow drawn from (${start.latitude.toFixed(4)}, ${start.longitude.toFixed(4)}) to (${end.latitude.toFixed(4)}, ${end.longitude.toFixed(4)})`,
          type: 'arrow',
          coordinates: { start, end },
          color: borderColor,
        };
      } else {
        return {
          success: true, // Line was drawn successfully
          message: `Arrow line drawn from (${start.latitude.toFixed(4)}, ${start.longitude.toFixed(4)}) to (${end.latitude.toFixed(4)}, ${end.longitude.toFixed(4)}) (arrowhead may not be visible)`,
          type: 'arrow',
          coordinates: { start, end },
          color: borderColor,
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw arrow',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Draw grid tool
export const drawGridTool = tool({
  description:
    'Draw a grid of rectangles on the map using center point, rows, and columns (NOT for drawing single rectangles)',
  inputSchema: z.object({
    center: z.object({
      latitude: z.number().describe('Center latitude of the grid'),
      longitude: z.number().describe('Center longitude of the grid'),
    }),
    rows: z.number().min(1).max(10).describe('Number of rows in the grid'),
    columns: z
      .number()
      .min(1)
      .max(10)
      .describe('Number of columns in the grid'),
    cellSize: z
      .number()
      .min(0.01)
      .max(5)
      .describe('Size of each grid cell in kilometers'),
    color: z.string().optional().describe('Color of the grid lines'),
    fillColor: z.string().optional().describe('Fill color of the grid cells'),
    opacity: z
      .number()
      .min(0)
      .max(1)
      .optional()
      .describe('Opacity of the grid'),
  }),
  execute: async ({
    center,
    rows,
    columns,
    cellSize,
    color = 'blue',
    fillColor,
    opacity = 0.3,
  }) => {
    try {
      const borderColor = parseColor(color);
      const fill = fillColor ? parseColor(fillColor) : borderColor;

      // Calculate grid bounds
      const latOffset = (cellSize * rows) / 111; // Approximate km to degrees
      const lngOffset =
        (cellSize * columns) /
        (111 * Math.cos((center.latitude * Math.PI) / 180));

      const startLat = center.latitude - latOffset / 2;
      const startLng = center.longitude - lngOffset / 2;

      const cellLatSize = cellSize / 111;
      const cellLngSize =
        cellSize / (111 * Math.cos((center.latitude * Math.PI) / 180));

      // Draw each grid cell
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < columns; col++) {
          const cellStartLat = startLat + row * cellLatSize;
          const cellStartLng = startLng + col * cellLngSize;
          const cellEndLat = cellStartLat + cellLatSize;
          const cellEndLng = cellStartLng + cellLngSize;

          await mapController.drawRectangle({
            southwest: [cellStartLng, cellStartLat],
            northeast: [cellEndLng, cellEndLat],
            color: borderColor,
            fillColor: fill,
            opacity: opacity,
          });
        }
      }

      return {
        success: true,
        message: `Grid drawn with ${rows}x${columns} cells, each ${cellSize}km`,
        type: 'grid',
        coordinates: center,
        rows,
        columns,
        cellSize,
        color: borderColor,
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to draw grid',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Clear graphics tool
export const clearGraphicsTool = tool({
  description:
    'Clear drawn graphics from the map. Can clear all graphics or specific types',
  inputSchema: z.object({
    type: z
      .string()
      .optional()
      .describe(
        'Type of graphics to clear: "all", "lines", "points", "circles", "rectangles", "polygons", "arrows", "grids", "markers" (location markers). Default: "all"'
      ),
    color: z
      .string()
      .optional()
      .describe('Clear only graphics of specific color (e.g., "red", "blue")'),
  }),
  execute: async ({ type = 'all', color }) => {
    try {
      // Clear graphics from the map with specific type and color
      const result = await mapController.clearGraphics(type, color);

      if (result.success) {
        let message = 'Graphics cleared from the map';
        if (type !== 'all') {
          message = `${type} cleared from the map`;
        }
        if (color) {
          message += ` (${color} color only)`;
        }

        return {
          success: true,
          message,
          type: 'clear',
          clearedType: type,
          clearedColor: color,
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to clear graphics',
          error: 'Map clearing failed',
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Failed to clear graphics',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});
