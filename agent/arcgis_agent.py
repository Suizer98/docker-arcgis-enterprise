#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent

from prompts import get_system_prompt, get_simple_system_prompt

# Configuration
MODEL_NAME = "llama-3.1-8b-instant"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArcGISLangChainAgent:
    def __init__(self, memory_window_size: int = 10):
        self.groq_client = ChatGroq(
            model=MODEL_NAME,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )
        self.session_id = "default_session"
        self.mcp_server_url = os.getenv("MCP_SERVER_URL")
        if not self.mcp_server_url:
            raise ValueError("MCP_SERVER_URL environment variable is required")
        self.mcp_session = None
        
        # Memory configuration
        self.memory_window_size = memory_window_size
        self.memory = ConversationBufferWindowMemory(
            k=memory_window_size,
            memory_key="chat_history",
            return_messages=True
        )
        
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
                logger.info(f"Args type: {type(kwargs)}, Args content: {kwargs}")
                logger.info(f"Args keys: {list(kwargs.keys()) if kwargs else 'None'}")
                logger.info(f"Args values: {list(kwargs.values()) if kwargs else 'None'}")
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
                elif param_type == "array":
                    field_type = List[Any]
                elif param_type == "object":
                    field_type = Dict[str, Any]
                else:
                    field_type = str
                
                # Create field with proper default handling
                if param_required:
                    fields[param_name] = Field(description=param_description)
                    annotations[param_name] = field_type
                else:
                    # For optional parameters, always use Optional type
                    annotations[param_name] = Optional[field_type]
                    
                    # Set appropriate defaults based on type and provided default
                    if param_default is not None:
                        fields[param_name] = Field(default=param_default, description=param_description)
                    else:
                        # For optional parameters without explicit default, use sensible defaults
                        if field_type == bool:
                            fields[param_name] = Field(default=False, description=param_description)
                        elif field_type == int:
                            fields[param_name] = Field(default=0, description=param_description)
                        elif field_type == str:
                            fields[param_name] = Field(default="", description=param_description)
                        else:
                            # For complex types like arrays and objects, use None as default
                            fields[param_name] = Field(default=None, description=param_description)
            
            # Create the dynamic model
            class DynamicToolInput(BaseModel):
                __annotations__ = annotations
                
                class Config:
                    extra = "ignore"  # Ignore extra fields instead of allowing them
            
            # Add the fields to the model
            for field_name, field_def in fields.items():
                setattr(DynamicToolInput, field_name, field_def)
        else:
            # No parameters, create empty model that ignores extra fields
            class DynamicToolInput(BaseModel):
                class Config:
                    extra = "ignore"
        
        # Create a dynamic schema based on the function parameters from MCP
        parameters = function_info.get("parameters", {})
        
        if parameters:
            # Create a dynamic model with the correct field names and types
            fields = {}
            annotations = {}
            
            for param_name, param_info in parameters.items():
                param_type = param_info.get("type", "string")
                param_required = param_info.get("required", False)
                param_default = param_info.get("default")
                
                # Convert type string to Python type
                if param_type == "boolean":
                    field_type = bool
                elif param_type == "integer":
                    field_type = int
                elif param_type == "array":
                    field_type = List[Any]
                elif param_type == "object":
                    field_type = Dict[str, Any]
                else:
                    field_type = str
                
                # Create field with proper default handling
                if param_required:
                    fields[param_name] = Field(description=param_info.get("description", f"Parameter {param_name}"))
                    annotations[param_name] = field_type
                else:
                    # For optional parameters, use Optional type
                    annotations[param_name] = Optional[field_type]
                    
                    # Set appropriate defaults
                    if param_default is not None:
                        fields[param_name] = Field(default=param_default, description=param_info.get("description", f"Parameter {param_name}"))
                    else:
                        # Use sensible defaults based on type
                        if field_type == bool:
                            fields[param_name] = Field(default=False, description=param_info.get("description", f"Parameter {param_name}"))
                        elif field_type == int:
                            fields[param_name] = Field(default=0, description=param_info.get("description", f"Parameter {param_name}"))
                        elif field_type == str:
                            fields[param_name] = Field(default="", description=param_info.get("description", f"Parameter {param_name}"))
                        else:
                            fields[param_name] = Field(default=None, description=param_info.get("description", f"Parameter {param_name}"))
            
            # Create the dynamic model
            class DynamicToolInput(BaseModel):
                __annotations__ = annotations
                
                class Config:
                    extra = "ignore"  # Ignore extra fields
            
            # Add the fields to the model
            for field_name, field_def in fields.items():
                setattr(DynamicToolInput, field_name, field_def)
            
            schema = DynamicToolInput
        else:
            # No parameters, create empty model
            class EmptyInput(BaseModel):
                pass
            schema = EmptyInput
        
        return StructuredTool.from_function(
            func=dynamic_tool_func,
            name=function_info["name"],
            description=function_info.get("description", f"Call {function_info['name']}"),
            args_schema=schema
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
                    # Ensure we always send a JSON body, even if arguments is None
                    request_body = arguments if arguments is not None else {}
                    response = await client.post(url, json=request_body)
                
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
        
        tools_list = chr(10).join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        system_prompt = get_system_prompt(tools_list)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
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
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    def _create_simple_chain(self):
        """Create a simple chain without tools"""
        system_prompt = get_simple_system_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
        
        return prompt | self.groq_client | StrOutputParser()
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process user message using dynamically discovered tools with memory"""
        try:
            if not self._initialized:
                await self._initialize()
            else:
                self.current_tools_used = []
            
            try:
                # Get conversation history from memory
                chat_history = self.memory.chat_memory.messages
                
                # Add memory context to the input
                input_data = {
                    "input": message,
                    "chat_history": chat_history
                }
                
                result = await self.agent_executor.ainvoke(input_data)
                tools_used = self.current_tools_used.copy()
                
                # Get the output message with better error handling
                output = "No response generated"
                if result is None:
                    output = "No response generated from agent"
                elif isinstance(result, dict):
                    # Handle different possible result structures
                    if "output" in result:
                        output = result["output"]
                    elif "response" in result:
                        output = result["response"]
                    elif "message" in result:
                        output = result["message"]
                    elif "text" in result:
                        output = result["text"]
                    else:
                        # If it's a dict but no recognizable output field, convert to string
                        output = str(result)
                elif hasattr(result, 'output') and result.output is not None:
                    output = result.output
                elif hasattr(result, 'get') and result.get is not None:
                    output = result.get("output", "No response generated")
                else:
                    output = str(result) if result is not None else "No response generated"
                
                # Save the conversation to memory
                self.memory.save_context(
                    {"input": message},
                    {"output": output}
                )
                
            except Exception as agent_error:
                logger.error(f"Agent execution error: {agent_error}")
                output = f"I encountered an error while processing your request: {str(agent_error)}. Please try rephrasing your question."
                tools_used = self.current_tools_used.copy()
                
                # Save the error to memory as well
                self.memory.save_context(
                    {"input": message},
                    {"output": output}
                )
            
            return {
                "message": output,
                "session_id": self.session_id,
                "tools_used": tools_used,
                "metadata": {
                    "model": MODEL_NAME,
                    "framework": "langchain + dynamic mcp + memory",
                    "tools_discovered": len(self.tools),
                    "memory_window_size": self.memory_window_size
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
    
    def clear_memory(self):
        """Clear the conversation memory"""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    def get_memory_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        messages = self.memory.chat_memory.messages
        history = []
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                history.append({
                    "user": messages[i].content,
                    "assistant": messages[i + 1].content
                })
        return history
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of the current memory state"""
        messages = self.memory.chat_memory.messages
        return {
            "total_messages": len(messages),
            "conversation_pairs": len(messages) // 2,
            "memory_window_size": self.memory_window_size,
            "memory_usage_percentage": (len(messages) / (self.memory_window_size * 2)) * 100
        }
    
    def set_memory_window_size(self, new_size: int):
        """Update the memory window size (requires reinitialization)"""
        self.memory_window_size = new_size
        self.memory = ConversationBufferWindowMemory(
            k=new_size,
            memory_key="chat_history",
            return_messages=True
        )
        logger.info(f"Memory window size updated to {new_size}")
