import requests
import pickle
import csv

from settings import GONG_API_URL, GONG_KEY, GONG_SECRET


def get_user_list(cursor=None):
    response = requests.get(f"{GONG_API_URL}/v2/users", auth=(GONG_KEY, GONG_SECRET), params={'cursor': cursor})
    response.raise_for_status()
    return response.json()

# Get a list of all users in the Gong account, recursively using the cursor
def get_all_users():
    users = []
    cursor = None
    while True:
        user_json = get_user_list(cursor)
        users.extend(user_json['users'])
        if 'cursor' in user_json['records']:
            cursor = user_json['records']['cursor']
        else:
            break
    return users

# For each user, save the first name, last name, email and user ID to a CSV file
def save_user_map_as_csv_and_pickle(users):
    with open('user_list.csv', 'w') as f:
        fieldnames = ['id', 'first_name', 'last_name', 'email', 'active', 'telephonyEnabled']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for user in users:
            writer.writerow({
                'id': user['id'], 
                'first_name': user['firstName'], 
                'last_name': user['lastName'], 
                'email': user['emailAddress'],
                'active': user['active'], 
                'telephonyEnabled': user['settings']['telephonyCallsImported']
            })
    user_map = {}
    for user in users:
        if not user['active']:
            continue
        if not user['settings']['telephonyCallsImported']:
            continue
        # map full name to id
        user_map[f"{user['firstName']} {user['lastName']}"] = user['id']
        user_map[f"{user['firstName']} - {user['lastName']}"] = user['id']
        # map email to id
        user_map[user['emailAddress']] = user['id']
        # map id to id
        user_map[user['id']] = user['id']
        # map first namd and last initial to id
        user_map[f"{user['firstName']} {user['lastName'][0]}"] = user['id']
        # map first initial and last name to id
        user_map[f"{user['firstName'][0]} {user['lastName']}"] = user['id']
    with open('user_list.pickle', 'wb') as f:
        pickle.dump(user_map, f)

    for key, value in user_map.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    users = get_all_users()
    save_user_map_as_csv_and_pickle(users)