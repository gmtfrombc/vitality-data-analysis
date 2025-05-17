import signal
import time


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Execution timed out")


# Set timeout to 30 seconds
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

start_time = time.time()

try:
    from db_query import query_dataframe

    _df = query_dataframe(
        """SELECT COUNT(DISTINCT patients.id) AS patient_count FROM patients  INNER JOIN vitals ON patients.id = vitals.patient_id WHERE patients.active = 1 AND vitals.bmi > 30 """
    )

    # Extract scalar result from dataframe
    if _df.empty:
        results = 0
    else:
        try:
            # Get the first cell value from the dataframe
            result = _df.iloc[0, 0]
            results = float(result) if result is not None else 0
        except (ValueError, TypeError, IndexError):
            results = 0

    # Ensure results is a dictionary for threshold metadata
    if not isinstance(results, dict):
        # Wrap scalar result in a dictionary
        original_value = results
        results = {"scalar": original_value}

    # Add threshold visualization
    try:
        # Try to create threshold visualization
        results["threshold_info"] = {
            "direction": "above",
            "value": 30.0,
            "field": "bmi",
        }

        import numpy as np
        import pandas as pd

        # Find the data to visualize
        data_to_viz = None
        for var_name in dir():
            var = locals()[var_name]
            if isinstance(var, pd.DataFrame) and "bmi" in var.columns:
                data_to_viz = var
                break

        # If we found data with the threshold field, create visualization
        if data_to_viz is not None:
            # Create histogram data
            hist_data, bin_edges = np.histogram(data_to_viz["bmi"].dropna(), bins=20)
            results["hist_data"] = hist_data.tolist()
            results["bin_edges"] = bin_edges.tolist()
            results["threshold_value"] = 30.0
            results["threshold_direction"] = "above"

            # Calculate stats
            matching_condition = data_to_viz["bmi"] > 30.0
            results["matching_count"] = matching_condition.sum()
            results["total_count"] = len(data_to_viz)
            results["percentage"] = (
                (results["matching_count"] / results["total_count"]) * 100
                if results["total_count"] > 0
                else 0
            )
    except Exception as viz_error:
        # If visualization fails, continue without it
        results["viz_error"] = str(viz_error)


except TimeoutException:
    results = {"error": "Execution timed out (30 seconds)"}
except Exception as e:
    import traceback

    results = {"error": str(e), "traceback": traceback.format_exc()}
finally:
    # Cancel the alarm
    signal.alarm(0)
    execution_time = time.time() - start_time
    if "results" not in locals() or results is None:
        results = {"error": "No results were generated"}
    if isinstance(results, dict) and "execution_time" not in results:
        results["execution_time"] = execution_time
