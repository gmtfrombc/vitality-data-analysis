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
        """SELECT AVG(bmi) AS result FROM vitals INNER JOIN patients ON patients.id = vitals.patient_id WHERE patients.gender = 'M' """
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
