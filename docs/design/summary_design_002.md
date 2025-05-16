# Data Analysis Assistant Visualization Enhancement

## Overview

This document outlines a plan for implementing basic visualization capabilities in the Data Analysis Assistant that can function properly within the sandbox security restrictions. The current implementation attempts to use HoloViews/hvplot for visualizations, but these libraries are blocked in the sandbox environment, resulting in non-rendering mock objects being displayed in the UI.

## Background

The Data Analysis Assistant executes user queries in a sandbox environment for security reasons. This sandbox blocks certain imports, including visualization libraries like `holoviews` and `hvplot`. While other tabs in the application (Dashboard, Patient View) successfully render visualizations, they do so outside the sandbox environment. For the Data Analysis Assistant, visualizations generated during code execution in the sandbox cannot be rendered properly.

## Current Implementation Analysis

1. **Visualization Generation**: In the current system, visualizations are generated through code executed in the sandbox:
   - Various plotting functions (histogram, line_plot, etc.) in `app/utils/plots.py` attempt to create HoloViews objects
   - When running in the sandbox, these fail to import HoloViews and return mock objects

2. **Display Mechanism**: The UI attempts to display these mock objects in the Visualization tab:
   ```python
   if "bmi_plot" in self.analysis_result:
       self.visualization_pane.object = self.analysis_result["bmi_plot"]
   elif "visualization" in self.analysis_result:
       self.visualization_pane.object = self.analysis_result["visualization"]
   ```

3. **Mock System**: The system has a sophisticated mock object system that maintains structural compatibility with HoloViews but doesn't render actual visualizations.

## Proposed Solution

Implement an HTML/CSS-based visualization approach that works within sandbox restrictions:

1. Create HTML generators for common visualization types (starting with histograms)
2. Return these HTML visualizations wrapped in `hv.Div` objects that Panel can display
3. Integrate this as a fallback mechanism when running in the sandbox environment

## Implementation Approach

### 1. HTML Histogram Generator

Add a new function to `app/utils/plots.py` that creates HTML-based histograms:

```python
def html_histogram(bin_edges, counts, title="Distribution"):
    """Create a simple HTML/CSS histogram that works in sandbox."""
    max_count = max(counts) if counts else 1
    bars_html = ""
    
    for i, count in enumerate(counts):
        if i < len(bin_edges) - 1:
            # Calculate percentage height
            height_pct = (count / max_count * 100) if max_count > 0 else 0
            label = f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}"
            
            # Create a styled div for each bar
            bar = f"""
            <div class="bar-container" style="display:inline-block; width:{100/len(counts)}%; text-align:center;">
              <div class="bar" style="background-color:#3498db; height:{height_pct}%; margin:0 2px;"></div>
              <div class="label" style="font-size:10px; overflow:hidden;">{label}</div>
              <div class="count" style="font-size:10px;">{count}</div>
            </div>
            """
            bars_html += bar
    
    # Complete HTML with container and title
    html = f"""
    <div style="width:100%; padding:10px;">
      <div style="font-weight:bold; text-align:center; margin-bottom:10px;">{title}</div>
      <div style="display:flex; height:200px; align-items:flex-end;">
        {bars_html}
      </div>
    </div>
    """
    
    return hv.Div(html)
```

### 2. Modify Existing Histogram Function

Update the existing `histogram` function in `app/utils/plots.py` to use this HTML approach as a fallback:

```python
def histogram(df: pd.DataFrame, column: str, *, bins: int = 20, title: str | None = None):
    """Return a histogram plot for *column* of *df* using hvplot or HTML fallback."""
    # [Existing code for test environment detection]
    
    # Try to use hvplot/holoviews first
    try:
        import hvplot.pandas
        # [Existing code for real histogram]
    except Exception:
        try:
            import holoviews as hv
            # [Existing code for holoviews histogram]
        except Exception:
            # HTML fallback when in sandbox
            try:
                # Calculate histogram data
                data = df[column].dropna().to_numpy()
                counts, bin_edges = np.histogram(data, bins=bins)
                # Generate HTML histogram
                return html_histogram(bin_edges, counts, title=_title_default)
            except Exception:
                # Final fallback to lightweight mock
                return Element(_title_default, kdims=[column], vdims=[column])
```

### 3. Add HTML Bar Chart Generator

Similarly, implement an HTML-based bar chart for categorical data:

```python
def html_bar_chart(categories, values, title="Bar Chart"):
    """Create a simple HTML/CSS bar chart that works in sandbox."""
    max_value = max(values) if values else 1
    bars_html = ""
    
    for i, (category, value) in enumerate(zip(categories, values)):
        # Calculate percentage height
        height_pct = (value / max_value * 100) if max_value > 0 else 0
        
        # Create a styled div for each bar
        bar = f"""
        <div class="bar-container" style="display:inline-block; width:{100/len(categories)}%; text-align:center;">
          <div class="bar" style="background-color:#2ecc71; height:{height_pct}%; margin:0 2px;"></div>
          <div class="label" style="font-size:10px; overflow:hidden;">{category}</div>
          <div class="value" style="font-size:10px;">{value}</div>
        </div>
        """
        bars_html += bar
    
    # Complete HTML with container and title
    html = f"""
    <div style="width:100%; padding:10px;">
      <div style="font-weight:bold; text-align:center; margin-bottom:10px;">{title}</div>
      <div style="display:flex; height:200px; align-items:flex-end;">
        {bars_html}
      </div>
    </div>
    """
    
    return hv.Div(html)
```

### 4. Update Code Generation in `app/ai_helper.py`

Ensure the code generation for distribution analyses uses the enhanced histogram function:

```python
# In _generate_distribution_analysis_code function
code = (
    # [Existing imports]
    "from app.utils.plots import histogram\n\n"
    # [Rest of code]
    f"    # Create histogram visualization\n"
    f"    title = 'Distribution of {metric.title()}'\n"
    f"    viz = histogram(df, '{metric}', bins=15, title=title)\n"
    # [Rest of code]
)
```

## Benefits and Challenges

### Benefits
1. Works completely within the sandbox environment with no external dependencies
2. Simple implementation with standard HTML/CSS
3. Can be easily extended to other chart types (bar charts, line charts)
4. Provides immediate visual feedback to users
5. Won't break with changing versions of visualization libraries

### Challenges
1. Limited interactivity compared to full HoloViews/Bokeh
2. May require additional work for formatting and aesthetics
3. Not as feature-rich as dedicated visualization libraries
4. May need separate implementations for different chart types

## Next Steps

1. Implement the HTML histogram function in `app/utils/plots.py`
2. Test with basic distribution queries
3. Add HTML implementations for other common chart types (bar charts, line charts)
4. Add formatting options for better aesthetics
5. Consider adding minimal interactivity using JavaScript if needed in the future
6. Update documentation on visualization capabilities

## Conclusion

This approach provides a simple, sandbox-compatible visualization solution that will allow users to see histograms and other basic visualizations in the Data Analysis Assistant. While not as feature-rich as dedicated visualization libraries, it delivers the essential functionality needed for data exploration and understanding. 