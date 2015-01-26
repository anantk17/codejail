# Makefile for CodeJail

test:
	@echo "Running all tests with no proxy process"
	nosetests
	@echo "Running all tests with proxy process"
	CODEJAIL_PROXY=1 nosetests
