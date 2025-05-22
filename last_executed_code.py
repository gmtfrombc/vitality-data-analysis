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
    # SQL equivalent: SELECT COUNT(patient_id) FROM vitals v
    # Query data
    sql = """SELECT COUNT(*) as count FROM vitals v WHERE patients.active = 1"""
    # SQL equivalent: SELECT COUNT(*) FROM vitals v WHERE patients.active = 1
    df = query_dataframe(sql)
    if not df.empty and "count" in df.columns:
        results = int(df["count"].iloc[0])
    else:
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
