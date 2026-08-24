.PHONY: up up-ai up-ai-gpu down logs verify package

up:
	./start-osiel.sh

up-ai:
	./start-osiel.sh --with-ai

up-ai-gpu:
	./start-osiel.sh --with-ai-gpu

down:
	./stop-osiel.sh

logs:
	docker compose logs -f --tail=200

verify:
	npm run verify:handoff

package:
	npm run package:handoff
