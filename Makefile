.PHONY: help test coverage test-verbose test-specific coverage-html coverage-json clean install

help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Django OData Tableau - Commandes disponibles           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Installation et configuration:"
	@echo "  make install          Installer les dépendances"
	@echo ""
	@echo "🧪 Tests:"
	@echo "  make test             Exécuter tous les tests"
	@echo "  make test-verbose     Exécuter les tests avec verbosité"
	@echo "  make test-specific    Exécuter un test spécifique (make test-specific TEST=test_name)"
	@echo ""
	@echo "📊 Couverture:"
	@echo "  make coverage         Exécuter les tests avec coverage (affichage terminal)"
	@echo "  make coverage-html    Générer un rapport HTML de couverture"
	@echo "  make coverage-json    Générer un rapport JSON de couverture"
	@echo ""
	@echo "🧹 Nettoyage:"
	@echo "  make clean            Nettoyer les fichiers générés (.coverage, htmlcov, etc)"
	@echo ""
	@echo "📚 Exemples:"
	@echo "  make test                                    # Tous les tests"
	@echo "  make test-verbose                            # Tests avec détails"
	@echo "  make test-specific TEST=test_service_document"
	@echo "  make coverage                                # Coverage complet"
	@echo ""

install:
	@echo "📦 Installation des dépendances..."
	pip install -r requirements.txt -q
	@echo "✅ Dépendances installées"

test:
	@echo "🧪 Exécution des tests..."
	python -m pytest tests/ -v --tb=short

test-verbose:
	@echo "🧪 Exécution des tests (mode verbose)..."
	python -m pytest tests/ -vv --tb=long

test-specific:
	@echo "🧪 Exécution du test: $(TEST)"
	python -m pytest tests/ -k $(TEST) -v --tb=short

coverage:
	@echo "📊 Exécution des tests avec couverture..."
	python run_coverage.py

coverage-html:
	@echo "📊 Génération du rapport HTML..."
	python -m pytest tests/ \
		--cov=my_app \
		--cov-report=html \
		--cov-report=term-missing \
		-q
	@echo "✅ Rapport HTML généré: htmlcov/index.html"

coverage-json:
	@echo "📊 Génération du rapport JSON..."
	python -m pytest tests/ \
		--cov=my_app \
		--cov-report=json:.coverage.json \
		-q
	@echo "✅ Rapport JSON généré: .coverage.json"

clean:
	@echo "🧹 Nettoyage des fichiers générés..."
	rm -rf .coverage .coverage.json htmlcov/ .pytest_cache/ __pycache__/ .eggs/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Nettoyage terminé"

.DEFAULT_GOAL := help

