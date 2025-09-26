// Response processing and formatting for AI service
import type { ChatMessage } from './types';

export class ResponseProcessor {
  // Get user-friendly tool description
  static getToolDescription(toolName: string): string {
    const descriptions: { [key: string]: string } = {
      centerOnCurrentLocation: 'Center map on your current location',
      getMapState: 'Get current map state',
      setMapCenter: 'Set map center',
      setMapZoom: 'Set map zoom level',
      getCurrentLocation: 'Get your current location',
      drawLine: 'Draw a line',
      drawPolygon: 'Draw a polygon',
      drawCircle: 'Draw a circle',
      drawRectangle: 'Draw a rectangle',
      drawPoint: 'Draw a point/marker',
      clearGraphics: 'Clear all drawn graphics',
    };
    return descriptions[toolName] || toolName;
  }

  // Process tool results and format response text
  static processToolResults(toolResults: any[], responseText: string): string {
    if (!toolResults || toolResults.length === 0) {
      return responseText;
    }

    // Separate successful and failed results
    const successfulResults = toolResults.filter(
      result => result.output?.success
    );
    const failedResults = toolResults.filter(result => !result.output?.success);

    // Only show results section if there are any results
    if (successfulResults.length > 0 || failedResults.length > 0) {
      responseText += '\n\n**Results:**';
    }

    // Process successful results first
    successfulResults.forEach((toolResult, index) => {
      try {
        const toolResultData = toolResult.output as any;

        if (toolResultData) {
          // Show coordinates for geolocation results
          if (toolResultData.coordinates) {
            const lat =
              toolResultData.coordinates.latitude ||
              toolResultData.coordinates.lat;
            const lng =
              toolResultData.coordinates.longitude ||
              toolResultData.coordinates.lng;
            if (lat !== undefined && lng !== undefined) {
              responseText += `\n✅ Location: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            }
            // Removed accuracy display as requested
          }
          // Show location name (only for non-geolocation tools)
          if (
            toolResultData.location &&
            toolResult.toolName !== 'getCurrentLocation'
          ) {
            responseText += `\n🏙️ ${toolResultData.location}`;
          }
          // Show zoom level
          if (toolResultData.zoomLevel) {
            responseText += `\n🔍 Zoom: ${toolResultData.zoomLevel}`;
          }
          // Show drawing tool results
          if (
            toolResultData.type === 'line' &&
            toolResultData.coordinates &&
            toolResultData.coordinates.start &&
            toolResultData.coordinates.end
          ) {
            responseText += `\n📏 Line: ${toolResultData.coordinates.start.lat.toFixed(4)}, ${toolResultData.coordinates.start.lng.toFixed(4)} → ${toolResultData.coordinates.end.lat.toFixed(4)}, ${toolResultData.coordinates.end.lng.toFixed(4)}`;
          } else if (
            toolResultData.type === 'polygon' &&
            toolResultData.coordinates
          ) {
            responseText += `\n🔷 Polygon: ${toolResultData.coordinates.length} vertices`;
          } else if (
            toolResultData.type === 'circle' &&
            toolResultData.coordinates &&
            toolResultData.coordinates.center
          ) {
            responseText += `\n⭕ Circle: Center (${toolResultData.coordinates.center.lat.toFixed(4)}, ${toolResultData.coordinates.center.lng.toFixed(4)}), Radius: ${toolResultData.coordinates.radius}m`;
          } else if (
            toolResultData.type === 'rectangle' &&
            toolResultData.coordinates &&
            toolResultData.coordinates.southwest &&
            toolResultData.coordinates.northeast
          ) {
            responseText += `\n⬜ Rectangle: (${toolResultData.coordinates.southwest.latitude.toFixed(4)}, ${toolResultData.coordinates.southwest.longitude.toFixed(4)}) to (${toolResultData.coordinates.northeast.latitude.toFixed(4)}, ${toolResultData.coordinates.northeast.longitude.toFixed(4)})`;
          } else if (
            toolResultData.type === 'point' &&
            toolResultData.coordinates &&
            toolResultData.coordinates.lat !== undefined &&
            toolResultData.coordinates.lng !== undefined
          ) {
            responseText += `\n📍 Point: (${toolResultData.coordinates.lat.toFixed(4)}, ${toolResultData.coordinates.lng.toFixed(4)})${toolResultData.label ? ` - ${toolResultData.label}` : ''}`;
          } else if (
            toolResultData.type === 'location_with_marker' &&
            toolResultData.coordinates &&
            toolResultData.coordinates.lat !== undefined &&
            toolResultData.coordinates.lng !== undefined
          ) {
            responseText += `\n📍 Location marked: (${toolResultData.coordinates.lat.toFixed(4)}, ${toolResultData.coordinates.lng.toFixed(4)}) - Your Location`;
          } else if (toolResultData.type === 'clear') {
            responseText += `\n🗑️ All graphics cleared from map`;
          }
          // Show current map state
          if (toolResultData.state && toolResultData.state.center) {
            const stateLat =
              toolResultData.state.center.latitude ||
              toolResultData.state.center.lat;
            const stateLng =
              toolResultData.state.center.longitude ||
              toolResultData.state.center.lng;
            if (stateLat !== undefined && stateLng !== undefined) {
              responseText += `\n📊 Map Center: ${stateLat.toFixed(6)}, ${stateLng.toFixed(6)}, Zoom ${toolResultData.state.zoom || 'N/A'}`;
            }
          }
          if (
            toolResultData.currentState &&
            toolResultData.currentState.center
          ) {
            const currentLat =
              toolResultData.currentState.center.latitude ||
              toolResultData.currentState.center.lat;
            const currentLng =
              toolResultData.currentState.center.longitude ||
              toolResultData.currentState.center.lng;
            if (currentLat !== undefined && currentLng !== undefined) {
              responseText += `\n📊 Map Center: ${currentLat.toFixed(6)}, ${currentLng.toFixed(6)}, Zoom ${toolResultData.currentState.zoom || 'N/A'}`;
            }
          }
          // Show available operations
          if (toolResultData.availableOperations) {
            responseText += `\n🛠️ Available Operations:`;
            toolResultData.availableOperations.forEach((op: string) => {
              responseText += `\n• ${op}`;
            });
          }
          // Show web search results
          if (toolResultData.results && Array.isArray(toolResultData.results)) {
            responseText += `\n\n🔍 Search Results:`;
            toolResultData.results.forEach((result: any, index: number) => {
              responseText += `\n${index + 1}. **${result.name}** (${result.type})`;
              if (result.rating) {
                responseText += `\n   ⭐ Rating: ${result.rating}/5`;
              }
              if (result.address) {
                responseText += `\n   📍 Address: ${result.address}`;
              }
              if (result.distance) {
                responseText += `\n   📏 Distance: ${result.distance}`;
              }
              if (result.coordinates) {
                responseText += `\n   🗺️ Coordinates: ${result.coordinates.lat.toFixed(6)}, ${result.coordinates.lng.toFixed(6)}`;
              }
            });
          }
          // Show success message if no specific data to display
          if (
            !toolResultData.coordinates &&
            !toolResultData.location &&
            !toolResultData.zoomLevel &&
            !toolResultData.state &&
            !toolResultData.currentState &&
            !toolResultData.availableOperations &&
            !toolResultData.results
          ) {
            responseText += `\n✅ ${toolResultData.message || 'Operation completed successfully'}`;
          }
        }
      } catch (error) {
        console.error('Error processing successful tool result:', error);
        responseText += `\n⚠️ Error processing tool result: ${error instanceof Error ? error.message : 'Unknown error'}`;
      }
    });

    // Only show critical failed results (not minor ones like duplicate map centering)
    const criticalFailures = failedResults.filter(result => {
      const toolName = result.toolName;
      // Don't show failures for duplicate operations that succeeded later
      const hasSuccessfulOperation = successfulResults.some(
        success => success.toolName === toolName
      );
      // Don't show failures for map operations if we have successful ones
      const isMapOperation = [
        'setMapCenterAndZoom',
        'setMapCenter',
        'setMapZoom',
      ].includes(toolName);
      return !(isMapOperation && hasSuccessfulOperation);
    });

    if (criticalFailures.length > 0) {
      responseText += '\n\n**Issues:**';
      criticalFailures.forEach(toolResult => {
        try {
          const toolResultData = toolResult.output as any;
          if (toolResultData) {
            responseText += `\n❌ ${toolResultData.message || 'Operation failed'}`;
            if (toolResultData.error) {
              responseText += `\n   Error: ${toolResultData.error}`;
            }

            // Check if this is a geolocation failure and show permission prompt
            if (
              toolResult.toolName === 'getCurrentLocation' ||
              toolResult.toolName === 'centerOnCurrentLocation'
            ) {
              if (
                toolResultData.message &&
                toolResultData.message.includes('denied')
              ) {
                responseText += `\n\nPlease enable location permissions in your browser to use this feature.`;
              }
            }
          }
        } catch (error) {
          console.error('Error processing failed tool result:', error);
          responseText += `\n⚠️ Error processing tool result: ${error instanceof Error ? error.message : 'Unknown error'}`;
        }
      });
    }

    return responseText;
  }

  // Process tool calls and format response text
  static processToolCalls(toolCalls: any[], responseText: string): string {
    if (!toolCalls || toolCalls.length === 0) {
      return responseText;
    }

    // Group tool calls by type for cleaner display
    const toolCallGroups: { [key: string]: number } = {};
    toolCalls.forEach(toolCall => {
      const toolName = toolCall.toolName;
      toolCallGroups[toolName] = (toolCallGroups[toolName] || 0) + 1;
    });

    responseText += '\n\n**Map Operations Performed:**';

    // Show unique operations with counts if multiple
    Object.entries(toolCallGroups).forEach(([toolName, count]) => {
      const toolDescription = this.getToolDescription(toolName);
      if (count > 1) {
        responseText += `\n- ${toolDescription} (${count}x)`;
      } else {
        responseText += `\n- ${toolDescription}`;
      }
    });

    return responseText;
  }
}
