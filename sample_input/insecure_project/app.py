import hashlib
import os
import subprocess


def insecure_hash(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()


def run_user_command(user_input: str) -> str:
    # Intentional insecure example for scanner testing
    return subprocess.check_output(f"echo {user_input}", shell=True, text=True)


def parse_expression(expr: str) -> int:
    # Intentional insecure example for scanner testing
    return eval(expr)


if __name__ == "__main__":
    secret_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    db_password = "supersecret123"
    api_key = os.getenv("API_KEY", "AKIAIOSFODNN7EXAMPLE")
    print(insecure_hash(secret_token + db_password + api_key))
