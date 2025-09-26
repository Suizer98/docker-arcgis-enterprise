import { tool } from 'ai';
import { z } from 'zod';
import { mapController } from '../Map/mapController';

// Get user's current location tool
export const getCurrentLocationTool = tool({
  description:
    "Get the user's current location using browser geolocation (NO parameters needed - do not pass latitude/longitude)",
  inputSchema: z.object({}),
  execute: async () => {
    try {
      // Try geolocation with retry logic
      let result = await mapController.getCurrentLocation();
      let retryCount = 0;
      const maxRetries = 2;

      while (!result.success && retryCount < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms before retry
        result = await mapController.getCurrentLocation();
        retryCount++;
      }

      // Return a more detailed response that the AI service can process
      if (result.success && result.coordinates) {
        // Place a marker at the current location
        try {
          const markerResult = await mapController.drawPoint(
            result.coordinates.lat,
            result.coordinates.lng,
            '#FF0000', // Red marker
            12, // Size
            'Your Location', // Label
            'location' // Marker type for location markers
          );
        } catch (markerError) {
          console.error(
            'Failed to place marker at current location:',
            markerError
          );
        }

        // Recenter the map to the current location
        try {
          const recenterResult = await mapController.setCenterAndZoom(
            result.coordinates.lat,
            result.coordinates.lng,
            15 // Zoom level 15 for good detail
          );
        } catch (recenterError) {
          console.error(
            'Failed to recenter map to current location:',
            recenterError
          );
        }

        const response = {
          success: true,
          message: `Current location found and marked: ${result.coordinates.lat.toFixed(6)}, ${result.coordinates.lng.toFixed(6)}`,
          coordinates: result.coordinates,
          accuracy: result.accuracy,
          location: `Latitude: ${result.coordinates.lat.toFixed(6)}, Longitude: ${result.coordinates.lng.toFixed(6)}`,
          type: 'location_with_marker',
        };
        return response;
      } else {
        const response = {
          success: false,
          message: result.message || 'Failed to get current location',
          error: 'Geolocation failed',
        };
        return response;
      }
    } catch (error) {
      console.error('Geolocation error:', error);
      const response = {
        success: false,
        message: 'Failed to get current location',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
      return response;
    }
  },
});

// Center map on user's current location tool
export const centerOnCurrentLocationTool = tool({
  description:
    "Center the map on the user's current location using geolocation",
  inputSchema: z.object({}),
  execute: async () => {
    try {
      const result = await mapController.centerOnCurrentLocation();

      if (result.success && result.coordinates) {
        // Place a marker at the current location
        try {
          const markerResult = await mapController.drawPoint(
            result.coordinates.lat,
            result.coordinates.lng,
            '#FF0000', // Red marker
            12, // Size
            'Your Location', // Label
            'location' // Marker type for location markers
          );
        } catch (markerError) {
          console.error(
            'Failed to place marker at current location:',
            markerError
          );
        }

        return {
          success: true,
          message: `Map centered on your location and marked: ${result.coordinates.lat.toFixed(6)}, ${result.coordinates.lng.toFixed(6)}`,
          coordinates: result.coordinates,
          location: `Centered at: ${result.coordinates.lat.toFixed(6)}, ${result.coordinates.lng.toFixed(6)}`,
          type: 'location_with_marker',
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to center on current location',
          error: 'Geolocation or centering failed',
        };
      }
    } catch (error) {
      console.error('Center location error:', error);
      return {
        success: false,
        message: 'Failed to center on current location',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
});
