#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel
import uvicorn

# LangChain imports
from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent


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

# Dynamic tool schemas will be created based on MCP function definitions

class ArcGISLangChainAgent:
    def __init__(self):
        self.groq_client = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )
        self.session_id = "default_session"
        self.mcp_server_url = os.getenv("MCP_SERVER_URL")
        if not self.mcp_server_url:
            raise ValueError("MCP_SERVER_URL environment variable is required")
        self.mcp_session = None
        
        # Tools will be created dynamically
        self.tools = []
        self.agent_executor = None
        self._initialized = False
        self.function_info = {}  # Store function info from MCP server
        self.current_tools_used = []  # Track tools used in current request
    
    async def _initialize(self):
        """Initialize the agent with dynamic tools from MCP server"""
        if not self._initialized:
            self.tools = await self._create_langchain_tools_dynamic()
            self.agent_executor = self._create_agent_with_tools()
            self._initialized = True
        else:
            self.current_tools_used = []
    
    
    async def _connect_mcp(self):
        """Connect to MCP server"""
        if self.mcp_session is None:
            try:
                # For now, we'll use HTTP transport since FastAPI-MCP provides HTTP endpoints
                # In a full MCP implementation, this would use stdio or other MCP transports
                logger.info(f"Connecting to MCP server at: {self.mcp_server_url}")
                self.mcp_session = "connected"  # Placeholder for now
            except Exception as e:
                logger.error(f"Failed to connect to MCP server: {e}")
                self.mcp_session = None
    
    
    async def _discover_mcp_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from MCP server using list-functions endpoint"""
        try:
            import httpx
            
            base_url = self.mcp_server_url[:-4] if self.mcp_server_url.endswith("/mcp") else self.mcp_server_url
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/list-functions")
                if response.status_code == 200:
                    return response.json().get("functions", [])
                return []
        except Exception as e:
            logger.error(f"Error discovering MCP tools: {e}")
            return []

    def _create_dynamic_tool(self, function_info: Dict[str, Any]) -> BaseTool:
        """Create a LangChain tool dynamically from MCP function info"""
        
        def dynamic_tool_func(**kwargs) -> str:
            """Dynamic tool function that calls MCP endpoint"""
            try:
                import asyncio
                if function_info["name"] not in self.current_tools_used:
                    self.current_tools_used.append(function_info["name"])
                logger.info(f"Calling tool {function_info['name']} with args: {kwargs}")
                result = asyncio.run(self._call_mcp_tool_dynamic(function_info["name"], kwargs))
                logger.info(f"Tool {function_info['name']} result: {result[:200]}...")
                return result
            except Exception as e:
                logger.error(f"Error in tool {function_info['name']}: {e}")
                return f"Error: {str(e)}"
        
        # Create a proper schema based on the function parameters
        parameters = function_info.get("parameters", {})
        
        if parameters:
            # Create a dynamic model with the correct field names and types
            fields = {}
            annotations = {}
            
            for param_name, param_info in parameters.items():
                param_type = param_info.get("type", "string")
                param_description = param_info.get("description", f"Parameter {param_name}")
                param_default = param_info.get("default")
                param_required = param_info.get("required", False)
                
                # Convert type string to Python type
                if param_type == "boolean":
                    field_type = bool
                elif param_type == "integer":
                    field_type = int
                else:
                    field_type = str
                
                # Create field with proper default handling
                if param_required:
                    fields[param_name] = Field(description=param_description)
                    annotations[param_name] = field_type
                else:
                    # For optional parameters, use Optional type and provide default
                    if param_default is not None:
                        fields[param_name] = Field(default=param_default, description=param_description)
                        annotations[param_name] = Optional[field_type]
                    else:
                        # For optional parameters without explicit default, use None as default
                        if field_type == bool:
                            fields[param_name] = Field(default=False, description=param_description)
                            annotations[param_name] = Optional[field_type]
                        elif field_type == int:
                            fields[param_name] = Field(default=0, description=param_description)
                            annotations[param_name] = Optional[field_type]
                        else:
                            fields[param_name] = Field(default="", description=param_description)
                            annotations[param_name] = Optional[field_type]
            
            # Create the dynamic model
            class DynamicToolInput(BaseModel):
                __annotations__ = annotations
                
                class Config:
                    extra = "ignore"
            
            # Add the fields to the model
            for field_name, field_def in fields.items():
                setattr(DynamicToolInput, field_name, field_def)
        else:
            # No parameters, create empty model that ignores extra fields
            class DynamicToolInput(BaseModel):
                class Config:
                    extra = "ignore"
        
        return StructuredTool.from_function(
            func=dynamic_tool_func,
            name=function_info["name"],
            description=function_info.get("description", f"Call {function_info['name']}"),
            args_schema=DynamicToolInput
        )

    async def _call_mcp_tool_dynamic(self, function_name: str, arguments: dict = None) -> str:
        """Call MCP function dynamically based on discovered function info"""
        try:
            import httpx
            
            base_url = self.mcp_server_url[:-4] if self.mcp_server_url.endswith("/mcp") else self.mcp_server_url
            function_info = self.function_info.get(function_name)
            if not function_info:
                logger.error(f"Function {function_name} not found in function_info")
                return f"Error: Function {function_name} not found"
            
            endpoint = function_info.get("endpoint", f"/{function_name}")
            method = function_info.get("method", "POST")
            url = f"{base_url}{endpoint}"
            
            logger.info(f"Calling MCP endpoint: {url} with method {method}")
            logger.info(f"Arguments: {arguments}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=arguments if arguments else {})
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Response data type: {type(result)}")
                    return json.dumps(result, indent=2)
                else:
                    logger.error(f"HTTP error: {response.status_code} - {response.text}")
                    return f"Error: HTTP {response.status_code}: {response.text}"
        except Exception as e:
            logger.error(f"Exception in _call_mcp_tool_dynamic: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    async def _create_langchain_tools_dynamic(self) -> List[BaseTool]:
        """Create LangChain tools dynamically from MCP server"""
        tools = []
        mcp_functions = await self._discover_mcp_tools()
        self.function_info = {func["name"]: func for func in mcp_functions}
        
        for function_info in mcp_functions:
            try:
                tools.append(self._create_dynamic_tool(function_info))
            except Exception as e:
                logger.error(f"Failed to create tool {function_info.get('name', 'unknown')}: {e}")
        
        return tools

    async def _create_fallback_tools(self) -> List[BaseTool]:
        """Create fallback tools if MCP discovery fails"""
        return []
    
    def _create_agent_with_tools(self):
        """Create an agent with dynamically discovered tools"""
        if not self.tools:
            return self._create_simple_chain()
        
        system_prompt = f"""You are an AI assistant for ArcGIS Enterprise. You have access to the following tools:

{chr(10).join([f"- {tool.name}: {tool.description}" for tool in self.tools])}

IMPORTANT GUIDELINES:
1. When users ask about services, use list_services to get the complete categorized list
2. The list_services response includes:
   - "services": array of all services with category field
   - "categorized": object with "system", "hosted", "custom" arrays
   - "summary": counts for each category type
3. For categorization questions (e.g., "system services", "hosted services"), examine the categorized section
4. For specific service questions, search through the services array using partial matching
5. Each service has: name, type, folder, category, category_description
6. When calling get_service_details, you MUST provide both parameters:
   - service_name: the exact service name from the list_services response
   - folder: the exact folder name from the list_services response (use empty string "" if no folder)
7. Always base your answers on the actual data returned by the tools, not assumptions

RESPONSE INTERPRETATION:
- System services: ArcGIS internal tools and utilities (GPServer, SymbolServer, etc.)
- Hosted services: User-published data services (FeatureServer, MapServer in Hosted folder)
- Custom services: Other services that don't fit the above categories

TOOL USAGE EXAMPLES:
- To list all services with categorization: use the list_services tool (no parameters needed)
- To get service details: use get_service_details with service_name and folder parameters
- Example: get_service_details with service_name="TouristAttractions" and folder="Hosted"
- Example: get_service_details with service_name="SampleWorldCities" and folder=""

Use these tools to help users with ArcGIS operations. When users ask about services or need specific information, use the appropriate tools to get real data from the ArcGIS server."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_tool_calling_agent(
            llm=self.groq_client,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
    def _create_simple_chain(self):
        """Create a simple chain without tools"""
        system_prompt = """You are an AI assistant for ArcGIS Enterprise. You can help users with general questions about ArcGIS.

Be helpful and provide information about ArcGIS services and operations."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        return prompt | self.groq_client | StrOutputParser()
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process user message using dynamically discovered tools"""
        try:
            if not self._initialized:
                await self._initialize()
            else:
                self.current_tools_used = []
            
            try:
                result = await self.agent_executor.ainvoke({"input": message})
                tools_used = self.current_tools_used.copy()
                
                # Get the output message
                output = "No response generated"
                if result is None:
                    output = "No response generated from agent"
                elif isinstance(result, dict):
                    output = result.get("output", "No response generated")
                elif hasattr(result, 'output'):
                    output = result.output
                elif hasattr(result, 'get'):
                    output = result.get("output", "No response generated")
                else:
                    output = str(result)
            except Exception as agent_error:
                logger.error(f"Agent execution error: {agent_error}")
                output = f"I encountered an error while processing your request: {str(agent_error)}. Please try rephrasing your question."
                tools_used = self.current_tools_used.copy()
            
            return {
                "message": output,
                "session_id": self.session_id,
                "tools_used": tools_used,
                "metadata": {
                    "model": "llama-3.1-8b-instant",
                    "framework": "langchain + dynamic mcp",
                    "tools_discovered": len(self.tools)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "message": f"I encountered an error: {str(e)}. Please try again.",
                "session_id": self.session_id,
                "tools_used": [],
                "metadata": {"error": str(e)}
            }

# FastAPI app setup
app = FastAPI(
    title="ArcGIS Enterprise LangChain Agent",
    description="AI agent for ArcGIS Enterprise using LangChain and MCP",
    version="2.0.0"
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
        "endpoints": {
            "chat": "/chat",
            "health": "/health"
        }
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
            "tools_count": len(agent.tools)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "2.0.0"
        }

@app.get("/tools")
async def get_discovered_tools():
    """Get list of dynamically discovered tools from MCP server"""
    try:
        logger.info(f"Tools endpoint called - initialized: {agent._initialized}, tools count: {len(agent.tools)}")
        
        if not agent._initialized:
            logger.info("Agent not initialized, initializing now...")
            await agent._initialize()
        
        logger.info(f"After initialization - tools count: {len(agent.tools)}")
        
        tools_info = []
        for i, tool in enumerate(agent.tools):
            try:
                logger.info(f"Processing tool {i}: {type(tool)}")
                tool_info = {
                    "name": getattr(tool, 'name', f'tool_{i}'),
                    "description": getattr(tool, 'description', 'No description'),
                }
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    tool_info["args_schema"] = str(tool.args_schema)
                tools_info.append(tool_info)
                logger.info(f"Successfully processed tool: {tool_info['name']}")
            except Exception as e:
                logger.error(f"Error processing tool {i}: {e}")
                tools_info.append({
                    "name": f"error_{i}",
                    "description": f"Error processing tool: {str(e)}"
                })
        
        logger.info(f"Returning {len(tools_info)} tools")
        return {
            "tools": tools_info,
            "count": len(tools_info),
            "mcp_server_url": agent.mcp_server_url,
            "initialized": agent._initialized
        }
    except Exception as e:
        logger.error(f"Error in tools endpoint: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": str(e),
            "tools": [],
            "count": 0,
            "initialized": agent._initialized
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
            metadata=response["metadata"]
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY environment variable is required")
        exit(1)
    
    uvicorn.run(
        "langchain_agent:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
