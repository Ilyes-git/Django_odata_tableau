#!/usr/bin/env python
"""
Script pour exécuter les tests avec coverage et afficher un rapport formaté
"""

import subprocess
import json
import sys
from pathlib import Path


def print_header(title):
    """Affiche un en-tête formaté"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_section(title):
    """Affiche un titre de section"""
    print(f"\n📋 {title}")
    print("-" * 70)


def run_tests_with_coverage():
    """Exécute les tests avec pytest-cov"""
    print_header("🧪 EXÉCUTION DES TESTS AVEC COUVERTURE")

    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=my_app",
        "--cov=second_app",
        "--cov=vessel",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=json:.coverage.json",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def extract_coverage_score():
    """Extrait le score de couverture du rapport JSON"""
    try:
        with open(".coverage.json", "r") as f:
            data = json.load(f)
            summary = data.get("totals", {})
            return summary
    except FileNotFoundError:
        return None


def format_coverage_report(summary):
    """Formate et affiche le rapport de couverture"""
    if not summary:
        return

    print_header("📊 RÉSUMÉ DE LA COUVERTURE")

    metrics = {
        "num_statements": "Nombre de lignes",
        "covered_lines": "Lignes couvertes",
        "percent_covered": "Couverture %"
    }

    print()
    for key, label in metrics.items():
        if key in summary:
            value = summary[key]
            if key == "percent_covered":
                print(f"  ✅ {label:.<40} {value:.2f}%")
            else:
                print(f"  📌 {label:.<40} {int(value)}")

    # Couleur du score
    coverage_pct = summary.get("percent_covered", 0)
    if coverage_pct >= 80:
        status = "🟢 EXCELLENT"
    elif coverage_pct >= 60:
        status = "🟡 BON"
    elif coverage_pct >= 40:
        status = "🟠 ACCEPTABLE"
    else:
        status = "🔴 FAIBLE"

    print(f"\n  Statut: {status}")


def show_files_coverage():
    """Affiche la couverture par fichier"""
    print_section("COUVERTURE PAR FICHIER")

    try:
        result = subprocess.run(
            ["python", "-m", "coverage", "report"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
    except Exception as e:
        print(f"Erreur lors de la lecture du rapport: {e}")


def show_html_report_location():
    """Indique où trouver le rapport HTML"""
    html_dir = Path("htmlcov/index.html")
    if html_dir.exists():
        print_section("📄 RAPPORTS GÉNÉRÉS")
        print(f"\n  🌐 Rapport HTML : {html_dir.absolute()}")
        print(f"     Ouvrez dans votre navigateur pour plus de détails")


def main():
    """Fonction principale"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🐍 Django OData Tableau - Test Coverage Report".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    # Exécuter les tests
    success = run_tests_with_coverage()

    if not success:
        print("\n❌ Les tests ont échoué!")
        sys.exit(1)

    # Extraire et afficher la couverture
    summary = extract_coverage_score()
    format_coverage_report(summary)

    # Afficher les fichiers
    show_files_coverage()

    # Afficher le rapport HTML
    show_html_report_location()

    print_header("✅ RAPPORT TERMINÉ")
    print("\n")


if __name__ == "__main__":
    main()

