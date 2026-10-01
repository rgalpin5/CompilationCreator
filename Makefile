.PHONY: setup dev lint test

setup:
	bash setup.sh

dev:
	bash setup.sh dev

lint:
	bash setup.sh lint

test:
	bash setup.sh test
