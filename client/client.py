import xmlrpc.client


def send_to_docker(n):
    proxy = xmlrpc.client.ServerProxy("http://127.0.0.1:8000/")
    result = proxy.fibonacci(n)
    print(result)


if __name__ == '__main__':

    while True:
        user_input = input("insert number to compute Fibonacci Value:")

        try:
            send_to_docker(int(user_input))
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            continue
        except xmlrpc.client.Fault:
            print("Something unusual was sent from the other side of the connection.")
            continue
