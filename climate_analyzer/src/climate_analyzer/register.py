"""
Register climate analysis tools for NAT.
This wraps the standalone Python functions as NAT tools.
"""

import json
import os
from pydantic import BaseModel, Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig
from nat.builder.framework_enum import LLMFrameworkEnum

# Import standalone tools
from climate_analyzer.utils.climate_tools_simple import (
    load_climate_data,
    calculate_statistics,
    filter_by_country,
    find_extreme_years,
    create_visualization,
    list_countries,
    station_statistics,
)

# Import calculator agent
from climate_analyzer.utils.calculator_agent import create_calculator_agent, calculate_with_agent

# Base path to climate data
DATA_PATH = "climate_analyzer/data/temperature_annual.csv"

# 1. Input schemas tell LLM what each tool expects
class CalculateStatsInput(BaseModel):
    country: str = Field(
        default="",
        description="Country name to filter by (e.g., 'United States', 'France'). Leave empty for global statistics."
    )
    start_year: int = Field(
        default=None,
        description="Start year for filtering (inclusive). Leave empty to include all years."
    )
    end_year: int = Field(
        default=None,
        description="End year for filtering (inclusive). Leave empty to include all years."
    )

class FilterCountryInput(BaseModel):
    country_name: str = Field(
        description="Country name to filter by (e.g., 'United States', 'France', 'Japan')"
    )


class FindExtremeInput(BaseModel):
    n: int = Field(
        default=5,
        description="Number of years to return"
    )
    extreme_type: str = Field(
        default="warmest",
        description="Type of extreme: 'warmest' or 'coldest'"
    )


class CreateVisualizationInput(BaseModel):
    plot_type: str = Field(
        default="annual_trend",
        description=(
            "Type of plot to create:\n"
            "- 'annual_trend': Shows temperature trend over years (global or for specific country)\n"
            "- 'country_comparison': Automatically finds and displays the TOP 5 COUNTRIES with highest warming trends\n"
            "- 'monthly_pattern': Shows average temperature by month (requires monthly data)"
        )
    )
    country: str = Field(
        default="",
        description=(
            "Country name to focus on (only used for 'annual_trend' and 'monthly_pattern'). "
            "Leave empty for global. Ignored for 'country_comparison' which always shows top 5."
        )
    )
    save_path: str = Field(
        default="climate_plot.png",
        description="Path to save the plot image"
    )

class StationStatsInput(BaseModel):
    top_n: int = Field(
        default=10,
        description="Number of top countries to include in detailed rankings"
    )


class CalculatorInput(BaseModel):
    question: str = Field(
        description="A mathematical question or calculation request related to climate data"
    )


# Config classes for each tool
class CalculateStatisticsConfig(FunctionBaseConfig, name="calculate_statistics"):
    """Configuration for calculating climate statistics with year filtering."""
    pass


class ListCountriesConfig(FunctionBaseConfig, name="list_countries"):
    """Configuration for listing available countries."""
    pass


class FilterByCountryConfig(FunctionBaseConfig, name="filter_by_country"):
    """Configuration for filtering by country."""
    pass


class FindExtremeYearsConfig(FunctionBaseConfig, name="find_extreme_years"):
    """Configuration for finding extreme years."""
    pass


class CreateVisualizationConfig(FunctionBaseConfig, name="create_visualization"):
    """Configuration for creating visualizations."""
    pass

class StationStatisticsConfig(FunctionBaseConfig, name="station_statistics"):
    """Configuration for weather station statistics."""
    pass

class CalculatorAgentConfig(FunctionBaseConfig, name="calculator_agent"):
    """Configuration for the mathematical calculator agent."""
    pass


# Register tools using clean wrapper pattern
@register_function(config_type=CalculateStatisticsConfig)
async def calculate_statistics_tool(config: CalculateStatisticsConfig, builder: Builder):
    """Register tool for calculating climate statistics with year filtering."""
    # Load data once at startup
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(country: str = "", start_year: int = None, end_year: int = None) -> str:
        # Treat empty string as None for the underlying function
        country_param = None if country == "" else country
        result = calculate_statistics(df, country_param, start_year, end_year)
        return result  # Already returns JSON string
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=CalculateStatsInput,
        description=("Calculate temperature statistics globally or for a specific country, with optional year filtering. "
                     "Returns JSON with: mean_temperature (°C), min_temperature (°C), max_temperature (°C), "
                     "std_deviation (°C), num_records (count), trend_per_decade (°C/decade), "
                     "years_analyzed (actual year range analyzed), and country (if specified).")
    )


@register_function(config_type=ListCountriesConfig)
async def list_countries_tool(config: ListCountriesConfig, builder: Builder):
    """Register tool for listing available countries."""
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(dummy: str = "") -> str:
        # NAT requires at least one parameter, even if unused
        result = list_countries(df)
        return result  # Already returns JSON string
    
    yield FunctionInfo.from_fn(
        _wrapper,
        description="List all available countries in the climate dataset. Use this when unsure what countries are available."
    )


@register_function(config_type=FilterByCountryConfig)
async def filter_by_country_tool(config: FilterByCountryConfig, builder: Builder):
    """Register tool for filtering by country."""
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(country_name: str) -> str:
        result = filter_by_country(df, country_name)
        return result  # Already returns JSON string
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=FilterCountryInput,
        description="Get information about climate data for a specific country including number of stations and years covered."
    )


@register_function(config_type=FindExtremeYearsConfig)
async def find_extreme_years_tool(config: FindExtremeYearsConfig, builder: Builder):
    """Register tool for finding extreme years."""
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(n: int = 5, extreme_type: str = "warmest") -> str:
        result = find_extreme_years(df, n, extreme_type)
        return result  # Already returns JSON string
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=FindExtremeInput,
        description="Find the warmest or coldest years in the global temperature dataset."
    )


@register_function(config_type=CreateVisualizationConfig)
async def create_visualization_tool(config: CreateVisualizationConfig, builder: Builder):
    """Register tool for creating visualizations."""
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(
        plot_type: str = "annual_trend",
        country: str = "",
        save_path: str = "climate_plot.png"
    ) -> str:
        # Treat empty string as None for the underlying function
        country_param = None if country == "" else country
        result = create_visualization(df, plot_type, country_param, save_path)
        return result  # Already returns string
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=CreateVisualizationInput,
        description=(
            "Create and save climate data visualizations. "
            "For 'country_comparison' plot type, it AUTOMATICALLY finds and visualizes the TOP 5 countries "
            "with highest warming trends - no need to calculate trends separately. "
            "Also creates annual temperature trends and monthly patterns."
        )
    )

@register_function(config_type=StationStatisticsConfig)
async def station_statistics_tool(config: StationStatisticsConfig, builder: Builder):
    """Register tool for weather station statistics."""
    df = load_climate_data(DATA_PATH)
    
    async def _wrapper(top_n: int = 10) -> str:
        result = station_statistics(df, top_n)
        return result
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=StationStatsInput,
        description=(
            "Get weather station statistics by country, including which country has the most stations and rankings. "
            "Provide an integer top_n for number of countries."
        )
    )


@register_function(config_type=CalculatorAgentConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def calculator_agent_tool(config: CalculatorAgentConfig, builder: Builder):
    """Register the LangGraph calculator agent as a NAT tool."""
    
    # Get the LLM from the builder - lifted from config
    # Use LANGCHAIN wrapper for LangGraph (built on LangChain)
    llm = await builder.get_llm("calculator_llm", wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    # Create the calculator agent with the NAT-provided LLM
    calculator_agent = create_calculator_agent(llm)
    
    async def _wrapper(question: str) -> str:
        # Use the calculator agent to process the question
        result = calculate_with_agent(question, calculator_agent)
        
        # Format the response as a JSON string
        response = {
            "calculation_steps": result["steps"],
            "final_result": result["final_result"],
            "explanation": result["explanation"]
        }
        return json.dumps(response, indent=2)
    
    yield FunctionInfo.from_fn(
        _wrapper,
        input_schema=CalculatorInput,
        description=(
            "USE THIS TOOL for any mathematical calculations, computations, or numerical operations. "
            "This tool performs: compound growth rates (CAGR), percentage changes, weighted averages, "
            "future projections, forecasting, and multi-step mathematical calculations. "
            "ALWAYS use this tool when asked to: calculate, compute, solve, project, forecast, determine future values, "
            "find growth rates, calculate percentages, or perform any arithmetic operations. "
            "Examples: 'What will the temperature be in 2050?', 'Calculate the growth rate', "
            "'What is the percentage change?', 'Project future values'. "
            "This tool shows all calculation steps. If you have numerical data from other tools, "
            "include those numbers in your question to this calculator tool."
        )
    )
