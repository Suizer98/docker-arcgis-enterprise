// Main map tools export file - imports from separate modules
import {
  drawLineTool,
  drawPointTool,
  drawCircleTool,
  drawRectangleTool,
  drawPolygonTool,
  drawArrowTool,
  drawGridTool,
  clearGraphicsTool,
} from './drawingTools';
import {
  setMapCenterTool,
  setMapZoomTool,
  setMapCenterAndZoomTool,
  getMapStateTool,
  getMapInfoTool,
} from './mapControlTools';
import {
  getCurrentLocationTool,
  centerOnCurrentLocationTool,
} from './locationTools';

// Export all tools
export const mapTools = {
  // Map control tools
  setMapCenter: setMapCenterTool,
  setMapZoom: setMapZoomTool,
  setMapCenterAndZoom: setMapCenterAndZoomTool,
  getMapState: getMapStateTool,
  getMapInfo: getMapInfoTool,

  // Location tools
  getCurrentLocation: getCurrentLocationTool,
  centerOnCurrentLocation: centerOnCurrentLocationTool,

  // Drawing tools
  drawLine: drawLineTool,
  drawPoint: drawPointTool,
  drawCircle: drawCircleTool,
  drawRectangle: drawRectangleTool,
  drawPolygon: drawPolygonTool,
  drawArrow: drawArrowTool,
  drawGrid: drawGridTool,
  clearGraphics: clearGraphicsTool,
};

// Re-export individual tools for direct imports if needed
export {
  // Drawing tools
  drawLineTool,
  drawPointTool,
  drawCircleTool,
  drawRectangleTool,
  drawPolygonTool,
  drawArrowTool,
  drawGridTool,
  clearGraphicsTool,

  // Map control tools
  setMapCenterTool,
  setMapZoomTool,
  setMapCenterAndZoomTool,
  getMapStateTool,
  getMapInfoTool,

  // Location tools
  getCurrentLocationTool,
  centerOnCurrentLocationTool,
};
