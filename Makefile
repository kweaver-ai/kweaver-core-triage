REPO := kweaver-ai/kweaver-core
WEEK := $(shell date +%Y-W%V)
REPORT := reports/$(WEEK).md

.PHONY: weekly fetch report publish clean

weekly: fetch report
	@echo ""
	@echo "✅ Report ready: $(REPORT)"
	@echo "✋ Review it, then run: make publish"

fetch:
	@echo "📥 Fetching open issues from $(REPO)..."
	gh issue list -R $(REPO) --state open --limit 200 \
	  --json number,title,createdAt,updatedAt,author,labels,comments,body \
	  > /tmp/kweaver-issues.json
	@echo "   $$(jq length /tmp/kweaver-issues.json) issues fetched"

report:
	python3 src/triage.py

publish:
	git add reports/
	git commit -m "chore: weekly triage $(WEEK)"
	git push

clean:
	rm -f /tmp/kweaver-issues.json
