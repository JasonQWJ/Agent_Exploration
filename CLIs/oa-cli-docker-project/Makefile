SHELL := /bin/bash
PROJECT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
OA_CLI_SRC := /Users/jason/Documents/Agent_Exploration/CLIs/oa-cli
DASHBOARD_SRC := $(OA_CLI_SRC)/dashboard-src
WHEEL_DIR := $(PROJECT_DIR)/dist
COMPOSE := docker compose

.PHONY: help dashboard build dashboard-build wheel build up down restart logs ps health rebuild clean

help:
	@echo "Targets:"
	@echo "  make dashboard-build - Build dashboard static assets from dashboard-src"
	@echo "  make wheel           - Build fresh oa-cli wheel from source"
	@echo "  make build           - Build Docker image (includes dashboard assets in wheel)"
	@echo "  make up              - Start dashboard container"
	@echo "  make down            - Stop and remove container"
	@echo "  make restart         - Restart stack"
	@echo "  make logs            - Tail container logs"
	@echo "  make ps              - Show compose status"
	@echo "  make health          - Query dashboard health API"
	@echo "  make rebuild         - Build dashboard + wheel + image + restart"
	@echo "  make clean           - Stop stack and remove built wheel(s)"


dashboard-build:
	@cd "$(DASHBOARD_SRC)" && npm run build

wheel: dashboard-build
	@mkdir -p "$(WHEEL_DIR)"
	@python3 -m pip wheel --no-deps -w "$(WHEEL_DIR)" "$(OA_CLI_SRC)"

build: wheel
	@cd "$(PROJECT_DIR)" && $(COMPOSE) build

up:
	@cd "$(PROJECT_DIR)" && $(COMPOSE) up -d

down:
	@cd "$(PROJECT_DIR)" && $(COMPOSE) down

restart:
	@cd "$(PROJECT_DIR)" && $(COMPOSE) restart

logs:
	@cd "$(PROJECT_DIR)" && $(COMPOSE) logs -f

ps:
	@cd "$(PROJECT_DIR)" && $(COMPOSE) ps

health:
	@python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:3460/api/health', timeout=5).read().decode())"

rebuild: wheel
	@cd "$(PROJECT_DIR)" && $(COMPOSE) up --build -d

clean: down
	@rm -f "$(WHEEL_DIR)"/*.whl
