#!/usr/bin/env python3

import logging
import os
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel
import uvicorn
from dotenv import load_dotenv

from arcgis_agent import ArcGISLangChainAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for FastAPI
class ChatRequest(PydanticBaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(PydanticBaseModel):
    response: str
    session_id: str
    tools_used: List[str]
    metadata: Dict[str, Any]


# FastAPI app setup
app = FastAPI(
    title="ArcGIS Enterprise LangChain Agent",
    description="AI agent for ArcGIS Enterprise using LangChain and MCP",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = ArcGISLangChainAgent()


@app.get("/")
async def root():
    return {
        "message": "ArcGIS Enterprise LangChain Agent",
        "version": "2.0.0",
        "framework": "LangChain + MCP",
        "endpoints": {"chat": "/chat", "health": "/health", "tools": "/tools"},
    }


@app.get("/health")
async def health_check():
    try:
        # Test Groq connection
        test_response = await agent.groq_client.ainvoke("Hello")

        return {
            "status": "healthy",
            "groq_api": "connected",
            "mcp_server_url": agent.mcp_server_url,
            "version": "2.0.0",
            "framework": "LangChain + Dynamic MCP",
            "initialized": agent._initialized,
            "tools_count": len(agent.tools),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "version": "2.0.0"}


@app.get("/tools")
async def get_discovered_tools():
    """Get list of dynamically discovered tools from MCP server"""
    try:
        logger.info(
            f"Tools endpoint called - initialized: {agent._initialized}, tools count: {len(agent.tools)}"
        )

        if not agent._initialized:
            logger.info("Agent not initialized, initializing now...")
            await agent._initialize()

        logger.info(f"After initialization - tools count: {len(agent.tools)}")

        tools_info = []
        for i, tool in enumerate(agent.tools):
            try:
                logger.info(f"Processing tool {i}: {type(tool)}")
                tool_info = {
                    "name": getattr(tool, "name", f"tool_{i}"),
                    "description": getattr(tool, "description", "No description"),
                }
                if hasattr(tool, "args_schema") and tool.args_schema:
                    tool_info["args_schema"] = str(tool.args_schema)
                tools_info.append(tool_info)
                logger.info(f"Successfully processed tool: {tool_info['name']}")
            except Exception as e:
                tools_info.append(
                    {
                        "name": f"error_{i}",
                        "description": f"Error processing tool: {str(e)}",
                    }
                )

        logger.info(f"Returning {len(tools_info)} tools")
        return {
            "tools": tools_info,
            "count": len(tools_info),
            "mcp_server_url": agent.mcp_server_url,
            "initialized": agent._initialized,
        }
    except Exception as e:
        return {
            "error": str(e),
            "tools": [],
            "count": 0,
            "initialized": agent._initialized,
        }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Processing message: {request.message[:100]}")

        response = await agent.process_message(request.message)

        return ChatResponse(
            response=response["message"],
            session_id=response["session_id"],
            tools_used=response["tools_used"],
            metadata=response["metadata"],
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    load_dotenv()

    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY environment variable is required")
        exit(1)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
