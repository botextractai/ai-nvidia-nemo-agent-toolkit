"""
Simplified climate data analysis tools for the course.
These work with the pre-processed CSV files for easier use.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import matplotlib.pyplot as plt
import json


def load_climate_data(file_path: str = "temperature_annual.csv") -> pd.DataFrame:
    """
    Load climate temperature data from CSV file.
    
    Args:
        file_path: Path to the CSV file (monthly or annual)
        
    Returns:
        DataFrame with temperature data
    """
    df = pd.read_csv(file_path)
    return df


def calculate_statistics(df: pd.DataFrame, country: Optional[str] = None, start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
    """
    Calculate basic statistics from temperature data with proper year filtering.
    
    Args:
        df: DataFrame with temperature data
        country: Optional country name to filter by
        start_year: Optional start year for filtering
        end_year: Optional end year for filtering
        
    Returns:
        JSON string with statistics
    """
    # Filter by country if specified
    if country and 'country_name' in df.columns:
        df = df[df['country_name'] == country]
        if df.empty:
            return json.dumps({"error": f"No data found for country: {country}"})
    
    # Filter by year range if specified
    if 'year' in df.columns:
        if start_year is not None:
            df = df[df['year'] >= start_year]
        if end_year is not None:
            df = df[df['year'] <= end_year]
        if df.empty:
            return json.dumps({"error": f"No data found for the specified year range"})
    
    # Determine temperature column
    temp_col = 'annual_temperature' if 'annual_temperature' in df.columns else 'temperature'
    
    stats = {
        "mean_temperature": round(float(df[temp_col].mean()), 2),
        "min_temperature": round(float(df[temp_col].min()), 2),
        "max_temperature": round(float(df[temp_col].max()), 2),
        "std_deviation": round(float(df[temp_col].std()), 2),
        "num_records": len(df)
    }
    
    # Calculate trend for yearly data
    if 'year' in df.columns and 'annual_temperature' in df.columns:
        yearly_global = df.groupby('year')['annual_temperature'].mean()
        if len(yearly_global) > 1:
            years = yearly_global.index.values
            temps = yearly_global.values
            z = np.polyfit(years, temps, 1)
            stats['trend_per_decade'] = round(float(z[0] * 10), 3)
            stats['years_analyzed'] = f"{years.min()}-{years.max()}"
    
    if country:
        stats['country'] = country
        
    return json.dumps(stats, indent=2)


def filter_by_country(df: pd.DataFrame, country_name: str) -> pd.DataFrame:
    """
    Filter temperature data by country name.
    
    Args:
        df: Temperature data DataFrame
        country_name: Country name (e.g., 'United States', 'France')
        
    Returns:
        Filtered DataFrame as JSON string
    """
    filtered = df[df['country_name'] == country_name]
    
    if filtered.empty:
        return json.dumps({"error": f"No data found for country: {country_name}"})
    
    # Return summary info
    result = {
        "country": country_name,
        "stations": filtered['station_id'].nunique(),
        "records": len(filtered),
        "years": f"{filtered['year'].min()}-{filtered['year'].max()}",
        "stations_list": filtered[['station_id', 'name']].drop_duplicates().to_dict('records')
    }
    
    return json.dumps(result, indent=2)


def create_visualization(df: pd.DataFrame, 
                        plot_type: str = "annual_trend",
                        country: Optional[str] = None,
                        save_path: str = "climate_plot.png") -> str:
    """
    Create climate data visualizations and save to file.
    
    Args:
        df: Temperature data DataFrame
        plot_type: Type of plot ('annual_trend', 'country_comparison', 'monthly_pattern')
        country: Optional country to focus on
        save_path: Path to save the plot
        
    Returns:
        Description of what was plotted
    """
    plt.figure(figsize=(10, 6))
    
    # Filter by country if specified
    if country and 'country_name' in df.columns:
        df = df[df['country_name'] == country]
        if df.empty:
            return f"No data found for country: {country}"
    
    if plot_type == "annual_trend":
        # Calculate global annual means
        if 'annual_temperature' in df.columns:
            annual_means = df.groupby('year')['annual_temperature'].mean()
        else:
            annual_means = df.groupby('year')['temperature'].mean()
        
        plt.plot(annual_means.index, annual_means.values, 'b-', linewidth=2)
        plt.scatter(annual_means.index, annual_means.values, alpha=0.6)
        
        # Add trend line
        z = np.polyfit(annual_means.index, annual_means.values, 1)
        p = np.poly1d(z)
        plt.plot(annual_means.index, p(annual_means.index), "r--", alpha=0.8, 
                label=f'Trend: {z[0]*10:.3f}°C/decade')
        
        plt.xlabel('Year')
        plt.ylabel('Temperature (°C)')
        title = f'Annual Average Temperature Trend'
        if country:
            title += f' - {country}'
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
    elif plot_type == "country_comparison" and 'country_name' in df.columns:
        # Compare top 5 countries by temperature change
        country_trends = {}
        for country_name in df['country_name'].unique():
            country_data = df[df['country_name'] == country_name]
            if 'annual_temperature' in df.columns:
                yearly = country_data.groupby('year')['annual_temperature'].mean()
            else:
                yearly = country_data.groupby('year')['temperature'].mean()
            
            if len(yearly) > 10:  # Need enough data for trend
                z = np.polyfit(yearly.index, yearly.values, 1)
                country_trends[country_name] = z[0] * 10  # Per decade
        
        # Sort by trend and plot top 5
        sorted_countries = sorted(country_trends.items(), key=lambda x: x[1], reverse=True)[:5]
        
        countries = [c[0] for c in sorted_countries]
        trends = [c[1] for c in sorted_countries]
        
        plt.bar(countries, trends, color='coral', edgecolor='darkred')
        plt.xlabel('Country')
        plt.ylabel('Temperature Trend (°C/decade)')
        plt.title('Top 5 Countries by Warming Trend')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        
    elif plot_type == "monthly_pattern" and 'month' in df.columns:
        # Monthly temperature pattern
        monthly_means = df.groupby('month')['temperature'].mean()
        
        plt.bar(monthly_means.index, monthly_means.values, color='skyblue', edgecolor='navy')
        plt.xlabel('Month')
        plt.ylabel('Average Temperature (°C)')
        title = 'Monthly Temperature Pattern'
        if country:
            title += f' - {country}'
        plt.title(title)
        plt.xticks(range(1, 13), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        plt.grid(True, alpha=0.3)
    
    else:
        plt.close()
        return f"Plot type '{plot_type}' not available for this data"
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Created {plot_type} plot and saved to {save_path}"


def list_countries(df: pd.DataFrame) -> str:
    """
    List all available countries in the dataset.
    
    Args:
        df: Temperature data DataFrame
        
    Returns:
        JSON string with list of countries
    """
    countries = sorted(df['country_name'].unique())
    
    return json.dumps({
        "available_countries": countries,
        "total_count": len(countries)
    }, indent=2)


def find_extreme_years(df: pd.DataFrame, n: int = 5, extreme_type: str = "warmest") -> str:
    """
    Find the warmest or coldest years globally.
    
    Args:
        df: Temperature data DataFrame  
        n: Number of years to return
        extreme_type: 'warmest' or 'coldest'
        
    Returns:
        JSON string with extreme years
    """
    # Calculate global annual means
    if 'annual_temperature' in df.columns:
        annual_means = df.groupby('year')['annual_temperature'].mean()
    else:
        annual_means = df.groupby('year')['temperature'].mean()
    
    # Sort appropriately
    sorted_years = annual_means.sort_values(ascending=(extreme_type == 'coldest'))
    
    results = []
    for i, (year, temp) in enumerate(sorted_years.head(n).items()):
        results.append({
            "rank": i + 1,
            "year": int(year),
            "temperature": round(float(temp), 2)
        })
    
    return json.dumps({
        "type": extreme_type,
        "years": results
    }, indent=2)

def station_statistics(df: pd.DataFrame, top_n: int = 10) -> str:
    """
    Get weather station statistics by country, including rankings.
    
    Args:
        df: DataFrame with temperature data
        top_n: Number of top countries to include in detail (default 10)
        
    Returns:
        JSON string with station statistics and rankings
    """
    # Count unique stations per country using the correct column name
    station_counts = df.groupby('country_name')['station_id'].nunique().sort_values(ascending=False)
    
    # Get total statistics
    total_stations = df['station_id'].nunique()
    total_countries = len(station_counts)
    
    # Create ranking list
    rankings = []
    for i, (country, count) in enumerate(station_counts.head(top_n).items()):
        rankings.append({
            "rank": i + 1,
            "country": country,
            "station_count": int(count),
            "percentage_of_total": round(count / total_stations * 100, 1)
        })
    
    result = {
        "total_stations": int(total_stations),
        "total_countries": total_countries,
        "country_with_most_stations": {
            "name": station_counts.index[0],
            "count": int(station_counts.iloc[0])
        },
        "top_countries_by_stations": rankings,
        "summary": f"{station_counts.index[0]} has the most weather stations with {int(station_counts.iloc[0])} stations ({round(station_counts.iloc[0] / total_stations * 100, 1)}% of all stations)"
    }
    
    return json.dumps(result, indent=2)


# Test functions
if __name__ == "__main__":
    # Test with the prepared CSV data
    import os
    
    # Path to the CSV files
    base_path = "../../climate_analyzer/data/"
    annual_file = os.path.join(base_path, "temperature_annual.csv")
    
    if os.path.exists(annual_file):
        print("Testing with prepared CSV data...\n")
        
        # Load data
        df = load_climate_data(annual_file)
        print(f"Loaded {len(df)} records")
        
        # Global statistics
        print("\nGlobal statistics:")
        print(calculate_statistics(df))
        
        # Country statistics
        print("\nUnited States statistics:")
        print(calculate_statistics(df, "United States"))
        
        # Find extreme years
        print("\nWarmest years globally:")
        print(find_extreme_years(df, n=5, extreme_type="warmest"))
        
        # Create visualization
        print("\nCreating visualization...")
        result = create_visualization(df, plot_type="annual_trend", save_path="test_plot.png")
        print(result)
        
        # Clean up
        if os.path.exists("test_plot.png"):
            os.remove("test_plot.png")
            print("Test plot cleaned up")
    else:
        print(f"CSV file not found at {annual_file}")
