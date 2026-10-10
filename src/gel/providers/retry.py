import time
import groq
from google.genai import errors

class RetryableError(Exception):
    pass


def with_retry(func, max_retries=3, base_delay=1, retryable_exceptions=(Exception,)):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
    raise last_exception




if __name__ == "__main__":
    attempt_count = 0

    def flaky_function():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError(f"simulated failure #{attempt_count}")
        return "success!"

    result_5 = with_retry(flaky_function, max_retries=5, base_delay=1, retryable_exceptions=(ValueError,))
    print(f"result:{result_5}")
    attempt_count = 0

    try:
        result_2 = with_retry(flaky_function, max_retries=2, base_delay=1, retryable_exceptions=(ValueError,))
        print(result_2)
    except ValueError as e:
        print("result_2 correctly raised:", e)

