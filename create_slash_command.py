import argparse
import json
import os

import requests
import dotenv

dotenv.load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("--guild", required=False, help="Permet de spécifier un serveur.")
parser.add_argument("--update", required=False, action="store_true", help="Permet de mettre à jour la commande.")
parser.add_argument("--delete", required=False, action="store_true", help="Permet de supprimer la commande.")
args = parser.parse_args()

try:
    with open(f"ressources/slash_commands/{args.name}.json", "r", encoding="utf-8") as f:
        json_command = json.load(f)
except FileNotFoundError:
    print("La commande n'a pas été trouvée")
else:
    headers = {
        "Authorization": f"Bot {os.getenv('BOT_TOKEN')}"
    }

    url = f"https://discord.com/api/v8/applications/{os.getenv('CLIENT_ID')}{'/guilds/'+args.guild if args.guild else ''}/commands"
    method = "POST"

    if args.update or args.delete:
        r = requests.get(url, headers=headers)
        try:
            command = (cmd for cmd in r.json() if cmd.get('name') == args.name).__next__()
        except StopIteration:
            print("Cette commande n'existe pas encore.")
            exit()
        else:
            url += '/'+command['id']
            method = "PATCH" if args.update else "DELETE"

    r = requests.request(method, url, headers=headers, json=json_command)
    print(r.content if r.status_code != 200 else "Effectué avec succès !")
