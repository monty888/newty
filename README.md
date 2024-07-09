# newty
messing around with python, nostr and qt

# install
```sh
git clone https://github.com/monty888/newty.git
cd newty
python3 -m venv venv
source venv/bin/activate
pip install .
```

# account
Keystore for nostr accounts.

![create accounts](account.png) 
```shell
TODO...
```

# signer
Basic NIP46 signer app, accounts can be created imported using the account app.

![NIP46 signer](signer.png) 
```shell
python -m newty.signer_app
```


# basic query
Make basic query request to nostr relays.  

![nostr basic query tool](basic_query.png) 
```shell
python basic_query.py
```

