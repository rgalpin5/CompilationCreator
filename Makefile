.PHONY: setup dev lint test api-types

setup:
	bash setup.sh

dev:
	bash setup.sh dev

lint:
	bash setup.sh lint

test:
	bash setup.sh test

api-types:
	bash setup.sh api-types
