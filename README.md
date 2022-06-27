# X3cli
A command line interface for [X3](https://x3.nodum.io).

# Installation
```sh
git clone git@github.com:timotk/x3cli.git
cd x3cli
pip install --user --prefer-binary .
```

# Usage
Simply run it using `x3` on the command line:
```sh
$ x3
Loading...
Username: timouelen@godatadriven.com
Password:
Input your 2FA code: ******
✓ geldig
✓ lines
✓ illness

Summary:
┏━━━━━━━━━━┳━━━━━━━━━┓
┃ project  ┃   time  ┃
┡━━━━━━━━━━╇━━━━━━━━━┩
│ Client A │    160  │
│  Holiday │      8  │
│     Idle │      8  │
│    Total │ 176/176 │
└──────────┴─────────┘
```

You can also be more specific:
```sh
x3 -y 2022 -m 1
```

# Security notice
After logging in, your session will be stored on disk.
When the login expires, you will be asked for your credentials again.
