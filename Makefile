.ONESHELL:
SHELL = /bin/bash
export BASH_ENV = bash_env

TAG = p4a
PREVIOUS = $(TAG):previous

.PHONY: all
all:
	docker build .
	image=$$(docker build -q .)
	docker tag '$(TAG)' '$(PREVIOUS)' || true
	docker tag $$image '$(TAG)'
	docker rmi '$(PREVIOUS)' || true
