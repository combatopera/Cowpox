# Cowpox
Deploy Android apps written in Python

## Quick start
* To simply use Cowpox you shouldn't need to build anything as an image is available on [Docker Hub](https://hub.docker.com/r/combatopera/cowpox)
* See [android-hello-world](https://github.com/combatopera/android-hello-world/blob/trunk/README.md) for an example project that Cowpox can turn into an Android APK

## Install
These are generic installation instructions.

### To use, permanently
The quickest way to get started is to install the current release from PyPI:
```
pip3 install --user Cowpox
```

### To use, temporarily
If you prefer to keep .local clean, install to a virtualenv:
```
python3 -m venv venvname
venvname/bin/pip install Cowpox
. venvname/bin/activate
```

### To develop
First clone the repo using HTTP or SSH:
```
git clone https://github.com/combatopera/Cowpox.git
git clone git@github.com:combatopera/Cowpox.git
```
Now use pyven's pipify to create a setup.py, which pip can then use to install the project editably:
```
python3 -m venv pyvenvenv
pyvenvenv/bin/pip install pyven
pyvenvenv/bin/pipify Cowpox

python3 -m venv venvname
venvname/bin/pip install -e Cowpox
. venvname/bin/activate
```

## Commands

### Cowpox
Build APK for project.

### Cowpox-servant
Containerised component, not for direct invocation.

## Licensing
* Cowpox as a whole is provided under the terms of the GPL, see [COPYING](COPYING)
* The [MIT](MIT) tree is additionally/instead provided under [LICENSE.kivy](LICENSE.kivy)
  * This covers all Cowpox code that can end up in your APK
* Cowpox is in essence a heavily refactored [Buildozer](https://github.com/kivy/buildozer) and [python-for-android](https://github.com/kivy/python-for-android), without which it would not exist

## Contact
* DMs open [@Cowpox2020](https://twitter.com/Cowpox2020)
