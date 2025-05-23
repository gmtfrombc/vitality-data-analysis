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
    # Generated code for BMI analysis
    # SQL equivalent: SELECT AVG(bmi) FROM vitals
    # Using avg() function to calculate mean BMI
    import app.db_query as db_query

    df = db_query.query_dataframe()
    # Calculate AVG(bmi) across all records
    results = df["bmi"].mean()


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
