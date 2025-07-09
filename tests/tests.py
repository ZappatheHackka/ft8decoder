from classes import MessageProcessor


with open("data.txt", 'r') as f:
    test_data = f.readlines()

test_data = [message.split("~")[-1] for message in test_data]
test_data = ["".join(message)[2:-1] for message in test_data]

print(test_data)