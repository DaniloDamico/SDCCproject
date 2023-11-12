import subprocess

if __name__ == "__main__":
    # Read the string value from the Redis database
    result = subprocess.run(["docker", "exec", "redis-container", "redis-cli", "GET", "faas"], capture_output=True, text=True)

    # Print the result
    if result.returncode == 0:
        print("Function code retrieved from Redis:")
        print(result.stdout.strip())
    else:
        print("Error retrieving function code from Redis.")
