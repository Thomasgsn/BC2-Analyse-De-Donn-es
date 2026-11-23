"""Complément réel : alternatives graphiques, exports et axe, sans appel LLM."""
import csv
import hashlib
import io
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

OUT = Path('/evidence')
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.goto('http://dashboard:8052/', wait_until='networkidle')
    expect(page.locator('#filter-status')).to_have_text('30000 observations dans la sélection.', timeout=30000)
    summary = page.locator('#projection-alternatives summary')
    summary.focus()
    page.keyboard.press('Enter')
    expect(page.locator('#projection-alternatives')).to_have_attribute('open', '')
    exports = {}
    for name in ['correlations', 'projections']:
        response = page.request.get('http://dashboard:8052/download/' + name + '.csv')
        assert response.status == 200
        assert 'attachment' in response.headers['content-disposition']
        raw = response.body()
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
        assert len(rows) > 1
        if name == 'projections':
            columns = rows[0]
            assert {'pc1', 'pc2', 'lda1', 'y'} <= set(columns)
            assert not any('id' == name.lower() for name in columns)
            assert {row[columns.index('y')] for row in rows[1:]} <= {'0', '1'}
            displayed = page.locator('#projection-alternatives tbody tr').all_text_contents()
            assert len(displayed) == 2
        else:
            assert len(rows) == len(rows[0])  # Carrée, plus en-têtes de ligne/colonne.
            for i in range(1, len(rows)):
                assert abs(float(rows[i][i]) - 1) < 1e-10
        exports[name] = {'rows': len(rows) - 1, 'columns': rows[0], 'sha256': hashlib.sha256(raw).hexdigest()}
    assert page.request.get('http://dashboard:8052/download/inconnu.csv').status == 404
    page.evaluate(Path('/opt/axe.min.js').read_text())
    result = page.evaluate("async () => await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
    (OUT / 'accessibility-followup-axe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    report = {'event': 'accessibility_followup', 'keyboard_details': True, 'exports': exports,
              'unknown_export_status': 404, 'violations': [v['id'] for v in result['violations']],
              'incomplete': [{'id': item['id'], 'nodes': len(item['nodes'])} for item in result['incomplete']],
              'scope': 'Vraie interface et exports ; contrôle automatique, pas de validation humaine WCAG.'}
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    report['mobile_global_overflow'] = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    page.screenshot(path=str(OUT / 'accessibility-followup-mobile.png'), full_page=True)
    (OUT / 'accessibility-followup.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    assert not report['violations'] and not report['mobile_global_overflow']
    browser.close()
