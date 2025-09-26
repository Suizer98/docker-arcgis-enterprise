import { tool } from 'ai';
import { z } from 'zod';
import { mapController } from '../Map/mapController';

// Set map center tool
export const setMapCenterTool = tool({
  description: 'Set the center of the map to specific coordinates',
  inputSchema: z.object({
    latitude: z
      .number()
      .min(-90)
      .max(90)
      .describe('The latitude coordinate (-90 to 90)'),
    longitude: z
      .number()
      .min(-180)
      .max(180)
      .describe('The longitude coordinate (-180 to 180)'),
    location: z
      .string()
      .optional()
      .describe('Optional: Human-readable location name'),
  }),
  execute: async ({ latitude, longitude, location }) => {
    try {
      const result = await mapController.setCenter(latitude, longitude);
      return {
        success: result.success,
        message: result.message,
        coordinates: { latitude, longitude },
        location: location || 'Unknown location',
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to set map center',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Set map zoom tool
export const setMapZoomTool = tool({
  description: 'Set the zoom level of the map',
  inputSchema: z.object({
    level: z
      .number()
      .min(1)
      .max(20)
      .describe(
        'The zoom level (1-20, where 1 is world view and 20 is street level)'
      ),
  }),
  execute: async ({ level }) => {
    try {
      const result = await mapController.setZoom(level);
      return {
        success: result.success,
        message: result.message,
        zoomLevel: level,
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to set zoom level',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Set map center and zoom tool
export const setMapCenterAndZoomTool = tool({
  description: 'Set both the center coordinates and zoom level of the map',
  inputSchema: z.object({
    latitude: z
      .number()
      .min(-90)
      .max(90)
      .describe('The latitude coordinate (-90 to 90)'),
    longitude: z
      .number()
      .min(-180)
      .max(180)
      .describe('The longitude coordinate (-180 to 180)'),
    zoom: z.number().min(1).max(20).describe('The zoom level (1-20)'),
    location: z
      .string()
      .optional()
      .describe('Optional: Human-readable location name'),
  }),
  execute: async ({ latitude, longitude, zoom, location }) => {
    try {
      const result = await mapController.setCenterAndZoom(
        latitude,
        longitude,
        zoom
      );
      return {
        success: result.success,
        message: result.message,
        coordinates: { latitude, longitude },
        zoomLevel: zoom,
        location: location || 'Unknown location',
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to set map view',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Get current map state tool
export const getMapStateTool = tool({
  description:
    'Get the current map state including center coordinates and zoom level',
  inputSchema: z.object({}),
  execute: async () => {
    try {
      const state = mapController.getCurrentState();
      if (!state) {
        return {
          success: false,
          message: 'Map not initialized',
        };
      }
      return {
        success: true,
        message: 'Current map state retrieved',
        state: {
          center: state.center,
          zoom: state.zoom,
        },
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to get map state',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});

// Get map information tool
export const getMapInfoTool = tool({
  description:
    'Get information about the current map state and available operations',
  inputSchema: z.object({}),
  execute: async () => {
    try {
      const state = mapController.getCurrentState();
      if (!state) {
        return {
          success: false,
          message: 'Map not initialized',
        };
      }
      return {
        success: true,
        message: 'Current map information retrieved',
        currentState: {
          center: state.center,
          zoom: state.zoom,
        },
        availableOperations: [
          'setMapCenter - Set map center to specific coordinates',
          'setMapZoom - Set zoom level (1-20)',
          'setMapCenterAndZoom - Set both center and zoom',
          'getMapState - Get current map state',
          "getCurrentLocation - Get user's current location using geolocation",
          "centerOnCurrentLocation - Center map on user's current location",
        ],
      };
    } catch (error) {
      return {
        success: false,
        message: 'Failed to get map information',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});
