.ONESHELL:
SHELL = /bin/bash
export BASH_ENV = bash_env

.PHONY: all
all:
	python3 setup.py bdist_wheel
