"""
Multi-Step Calculator Agent using LangGraph

A general-purpose mathematical calculation agent that can handle complex, multi-step calculations
with full transparency into the calculation process. The agent breaks down complex problems into
steps and uses appropriate mathematical tools to solve them.

AVAILABLE MATHEMATICAL TOOLS:
-----------------------------

1. basic_math(expression: str) -> float
   Description: Evaluate basic mathematical expressions
   Supports: +, -, *, /, ** (power), and parentheses
   Example: basic_math('(42.5 - 38.2) * 2.1')
   Use for: Simple arithmetic, order of operations, basic calculations

2. percentage_change(old_value: float, new_value: float) -> float
   Description: Calculate the percentage change between two values
   Formula: ((new_value - old_value) / old_value) * 100
   Example: percentage_change(old_value=35.2, new_value=28.7)
   Use for: Growth rates, comparing changes, trend analysis

3. compound_growth_rate(initial_value: float, final_value: float, periods: int) -> float
   Description: Calculate the Compound Annual Growth Rate (CAGR)
   Formula: ((final_value / initial_value) ** (1 / periods) - 1) * 100
   Example: compound_growth_rate(initial_value=14.2, final_value=15.8, periods=43)
   Use for: Long-term growth analysis, investment returns, multi-period trends

4. weighted_average(values_str: str, weights_str: str) -> float
   Description: Calculate weighted average of multiple values
   Inputs: Comma-separated strings of values and their corresponding weights
   Example: weighted_average('0.15,0.22,0.18', '320,1400,125')
   Use for: Population-weighted metrics, portfolio returns, grade calculations

5. calculate_final_value(initial_value: float, growth_rate: float, periods: int) -> float
   Description: Project future values based on compound growth
   Formula: initial_value * (1 + growth_rate/100) ** periods
   Example: calculate_final_value(450, -3.5, 5)
   Use for: Forecasting, projections, scenario planning

AGENT CAPABILITIES:
-------------------
- Handles complex multi-step calculations automatically
- Shows all intermediate calculation steps for transparency
- Manages calculation order and dependencies intelligently
- Provides clear explanations of the calculation process
- Automatically selects the appropriate tool for each step

EXAMPLE USAGE:
--------------
# Create calculator agent
calculator = create_calculator_agent(llm)

# Ask complex question
result = calculate_with_agent(
    "What's the compound growth rate if a value went from 14.2 to 15.8 over 43 periods?",
    calculator
)

# Result includes:
# - calculation_steps: List of all intermediate calculations
# - final_result: The final calculated value
# - explanation: Natural language explanation of the process
"""

import json
import re
from typing import TypedDict, Annotated, Sequence, Literal, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_nvidia_ai_endpoints import ChatNVIDIA
import operator


# State definition
class CalculatorState(TypedDict):
    """State for the calculator agent"""
    messages: Annotated[list[BaseMessage], operator.add]
    calculation_steps: list[str]
    final_result: float | None


# Tools for mathematical operations
@tool
def basic_math(expression: str) -> float:
    """
    Evaluate a basic mathematical expression.
    Supports +, -, *, /, **, and parentheses.
    
    Args:
        expression: A mathematical expression like "2 + 3 * 4" or "(10 - 5) ** 2"
    
    Returns:
        The result of the calculation
    """
    try:
        # Only allow safe mathematical operations
        allowed_chars = "0123456789+-*/().**"
        if not all(c in allowed_chars + " " for c in expression):
            raise ValueError(f"Invalid characters in expression: {expression}")
        
        # Evaluate the expression
        result = eval(expression)
        return float(result)
    except Exception as e:
        raise ValueError(f"Error evaluating expression '{expression}': {str(e)}")


@tool
def percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: The original value
        new_value: The new value
    
    Returns:
        Percentage change (positive for increase, negative for decrease)
    """
    if old_value == 0:
        raise ValueError("Cannot calculate percentage change from zero")
    return ((new_value - old_value) / old_value) * 100


@tool
def compound_growth_rate(initial_value: float, final_value: float, periods: int) -> float:
    """
    Calculate compound annual growth rate (CAGR).
    
    Args:
        initial_value: Starting value
        final_value: Ending value
        periods: Number of periods (e.g., years)
    
    Returns:
        Compound growth rate as a percentage
    """
    if initial_value <= 0 or final_value <= 0:
        raise ValueError("Values must be positive for CAGR calculation")
    if periods <= 0:
        raise ValueError("Number of periods must be positive")
    
    rate = (final_value / initial_value) ** (1 / periods) - 1
    return rate * 100


@tool
def weighted_average(values_str: str, weights_str: str) -> float:
    """
    Calculate weighted average of values.
    
    Args:
        values_str: Comma-separated list of values (e.g., "0.12,0.18,0.15")
        weights_str: Comma-separated list of weights (e.g., "150,200,100")
    
    Returns:
        Weighted average
    """
    # Parse comma-separated strings into lists of floats
    values = [float(v.strip()) for v in values_str.split(',')]
    weights = [float(w.strip()) for w in weights_str.split(',')]
    
    if len(values) != len(weights):
        raise ValueError("Values and weights must have the same length")
    if not weights or sum(weights) == 0:
        raise ValueError("Weights must sum to a non-zero value")
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / sum(weights)


@tool
def calculate_final_value(initial_value: float, growth_rate: float, periods: int) -> float:
    """
    Calculate final value given initial value, growth rate, and number of periods.
    
    Args:
        initial_value: Starting value
        growth_rate: Growth rate as a percentage (e.g., -3 for -3%)
        periods: Number of periods
    
    Returns:
        Final value after applying growth rate for specified periods
    """
    rate_decimal = growth_rate / 100
    return initial_value * ((1 + rate_decimal) ** periods)


# System prompt
SYSTEM_PROMPT = """You are a mathematical calculation assistant specializing in climate data analysis.

When given a calculation request:
1. Break it down into clear, sequential steps
2. Use the appropriate tools for each calculation
3. Show your work clearly
4. Provide a final answer with explanation

Available tools:
- basic_math: For arithmetic operations (+, -, *, /, **, parentheses)
- percentage_change: Calculate % change between two values
- compound_growth_rate: Calculate CAGR given initial, final, and periods
- weighted_average: Calculate weighted average (provide values and weights as comma-separated strings)
- calculate_final_value: Calculate final value given initial value, growth rate, and periods

Always think step by step and use tools for calculations."""


# Create the calculator agent - accepts optional LLM parameter
def create_calculator_agent(llm=None):
    """Create the calculator agent graph with provided or default LLM"""
    
    # Initialize LLM if not provided
    if llm is None:
        llm = ChatNVIDIA(
            model="meta/llama-3.1-70b-instruct",
            temperature=0.0,
            max_tokens=1024
        )
    
    # Bind tools to LLM
    tools = [basic_math, percentage_change, compound_growth_rate, weighted_average, calculate_final_value]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    # Define the agent function
    def agent(state: CalculatorState) -> dict:
        """Main agent function"""
        messages = state["messages"]
        
        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        # Get response from LLM
        response = llm_with_tools.invoke(messages)
        
        # Update calculation steps for tool calls
        calculation_steps = state.get("calculation_steps", [])
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                step_desc = f"{tool_call['name']}({', '.join(f'{k}={v}' for k, v in tool_call['args'].items())})"
                calculation_steps.append(step_desc)
        
        return {
            "messages": [response],
            "calculation_steps": calculation_steps
        }
    
    # Define conditional edge function
    def should_continue(state: CalculatorState) -> Literal["tools", "end"]:
        """Decide whether to continue"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, execute them
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Otherwise, end
        return "end"
    
    # Create graph
    graph = StateGraph(CalculatorState)
    
    # Add nodes
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    
    # Add edges
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()


def calculate_with_agent(question: str, calculator_agent) -> dict:
    """
    Main entry point for calculations using provided agent.
    
    Args:
        question: A mathematical question or calculation request
        calculator_agent: The compiled calculator agent
    
    Returns:
        Dictionary with result, steps, and explanation
    """
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "calculation_steps": [],
        "final_result": None
    }
    
    result = calculator_agent.invoke(initial_state)
    
    # Extract final result from steps
    final_result = None
    if result.get("calculation_steps"):
        # Try to extract numerical result from the last message
        last_ai_message = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break
        
        if last_ai_message:
            # Look for numbers in the final answer
            numbers = re.findall(r'-?\d+\.?\d*', last_ai_message.content)
            if numbers:
                # Take the last number as the final result
                try:
                    final_result = float(numbers[-1])
                except:
                    pass
    
    # Get the explanation from the last AI message
    explanation = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            explanation = msg.content
            break
    
    return {
        "question": question,
        "steps": result.get("calculation_steps", []),
        "final_result": final_result,
        "explanation": explanation
    }
