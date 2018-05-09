engineroom-wikipedia
--------------------

Install all Python dependencies in a virtualenv. You can use [brainsik's virtualenv-burrito](https://github.com/brainsik/virtualenv-burrito).

  * virtualenv-burrito:
```
    curl -sL https://raw.githubusercontent.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | $SHELL
```
  * make a new virtualenv
```
    mkvirtualenv -p $(which python3) engineroom3
```
  * install the dependencies
```
    pip install -r requirements.txt
```

You are good to go.
