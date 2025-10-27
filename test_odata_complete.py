#!/usr/bin/env python3
"""
Script de test complet pour l'API OData
Teste tous les endpoints et filtres supportés
"""

import requests
import json
from urllib.parse import urlencode

BASE_URL = "http://localhost:8000/odata"

def test_endpoint(name, url, params=None, is_xml=False):
    """Teste un endpoint et affiche les résultats"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

    try:
        if params:
            url_with_params = f"{url}?{urlencode(params)}"
            print(f"URL: {url_with_params}")
        else:
            print(f"URL: {url}")

        response = requests.get(url, params=params, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")

        if response.status_code == 200:
            # Gérer XML et JSON différemment
            if is_xml or 'xml' in response.headers.get('Content-Type', '').lower():
                # Pour XML, juste vérifier que c'est valide
                if response.text and response.text.startswith('<?xml'):
                    print(f"XML Response: Valid (length: {len(response.text)} chars)")
                    print(f"Sample: {response.text[:200]}...")
                    return True
                else:
                    print("Error: Invalid XML response")
                    return False
            else:
                # Pour JSON
                data = response.json()
                if isinstance(data, dict) and 'value' in data:
                    count = data.get('@odata.count', len(data['value']))
                    print(f"Count: {count}")
                    print(f"Returned items: {len(data['value'])}")
                    if data['value']:
                        print(f"Sample: {json.dumps(data['value'][0], indent=2, ensure_ascii=False)}")
                else:
                    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("OData API TESTS - Django OData Tableau")
    print("="*60)

    results = {}

    # 1. Service Document
    results['Service Document'] = test_endpoint(
        "Service Document",
        f"{BASE_URL}/"
    )

    # 2. Metadata
    results['Metadata XML'] = test_endpoint(
        "Metadata XML",
        f"{BASE_URL}/$metadata",
        is_xml=True
    )

    # 3. Collections
    results['Persons Collection'] = test_endpoint(
        "Get all Persons",
        f"{BASE_URL}/Persons"
    )

    results['Cars Collection'] = test_endpoint(
        "Get all Cars",
        f"{BASE_URL}/Cars"
    )

    # 4. Individual entities
    results['Person(1)'] = test_endpoint(
        "Get Person by ID",
        f"{BASE_URL}/Persons(1)"
    )

    results['Car(1)'] = test_endpoint(
        "Get Car by ID",
        f"{BASE_URL}/Cars(1)"
    )

    # 5. Filters - Comparaison
    results['Filter eq'] = test_endpoint(
        "Filter: first_name eq 'Lucie'",
        f"{BASE_URL}/Persons",
        {"$filter": "first_name eq 'Lucie'"}
    )

    results['Filter gt'] = test_endpoint(
        "Filter: year gt 2015",
        f"{BASE_URL}/Cars",
        {"$filter": "year gt 2015"}
    )

    results['Filter contains'] = test_endpoint(
        "Filter: last_name contains 'Marie'",
        f"{BASE_URL}/Persons",
        {"$filter": "last_name contains 'Marie'"}
    )

    results['Filter startswith'] = test_endpoint(
        "Filter: first_name startswith 'A'",
        f"{BASE_URL}/Persons",
        {"$filter": "first_name startswith 'A'"}
    )

    results['Filter endswith'] = test_endpoint(
        "Filter: last_name endswith 'ez'",
        f"{BASE_URL}/Persons",
        {"$filter": "last_name endswith 'ez'"}
    )

    # 6. Filters - Logique
    results['Filter OR'] = test_endpoint(
        "Filter: brand eq 'BMW' or brand eq 'Audi'",
        f"{BASE_URL}/Cars",
        {"$filter": "brand eq 'BMW' or brand eq 'Audi'"}
    )

    results['Filter AND'] = test_endpoint(
        "Filter: year gt 2015 and brand eq 'Volkswagen'",
        f"{BASE_URL}/Cars",
        {"$filter": "year gt 2015 and brand eq 'Volkswagen'"}
    )

    # 7. Orderby
    results['Orderby asc'] = test_endpoint(
        "OrderBy: year ascending",
        f"{BASE_URL}/Cars",
        {"$orderby": "year asc", "$top": "3"}
    )

    results['Orderby desc'] = test_endpoint(
        "OrderBy: year descending",
        f"{BASE_URL}/Cars",
        {"$orderby": "year desc", "$top": "3"}
    )

    # 8. Select
    results['Select'] = test_endpoint(
        "Select: brand, model only",
        f"{BASE_URL}/Cars",
        {"$select": "brand,model", "$top": "2"}
    )

    # 9. Pagination
    results['Skip and Top'] = test_endpoint(
        "Skip 2, Top 3",
        f"{BASE_URL}/Persons",
        {"$skip": "2", "$top": "3"}
    )

    # 10. Complex query
    results['Complex Query'] = test_endpoint(
        "Complex: filter + orderby + select + top",
        f"{BASE_URL}/Cars",
        {
            "$filter": "year gt 2015",
            "$orderby": "year desc",
            "$select": "brand,model,year",
            "$top": "3"
        }
    )

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

if __name__ == "__main__":
    main()

