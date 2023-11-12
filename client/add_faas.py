import subprocess

function_code = """
import sys

def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)
        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python <scriptname> <number>")
    else:
        try:
            num = int(sys.argv[1])
            result = fibonacci(num)
            print(f"The Fibonacci number at position {num} is: {result}")
        except ValueError:
            print("Please provide a valid integer as input.")
"""

if __name__ == "__main__":
    subprocess.run(["docker", "build", "-t", "redis-image", "."])
    subprocess.run(["docker", "run", "--name", "redis-container", "-d", "redis-image"])

    # Write a string into the Redis database
    subprocess.run(["docker", "exec", "redis-container", "redis-cli", "SET", "faas", function_code])

