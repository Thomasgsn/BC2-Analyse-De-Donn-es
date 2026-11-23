"""Vrai navigateur sur la section macro : séries, période, tableaux, export, axe et mobile."""
from pathlib import Path
import json,hashlib
from playwright.sync_api import sync_playwright,expect
out=Path('/evidence');out.mkdir(exist_ok=True,parents=True)
with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://dashboard:8052/#macro',wait_until='networkidle')
    section=page.locator('#macro').locator('..')
    expect(section.locator('.js-plotly-plot .gtitle')).to_contain_text('Retards de paiement',timeout=30000)
    expect(section).to_contain_text('Cohorte 2005')
    page.get_by_label('Dollar taïwanais pour 1 dollar US').check();expect(section.locator('.js-plotly-plot .gtitle')).to_contain_text('TWD/USD')
    page.get_by_label('5 ans').check();expect(section).not_to_contain_text('Cohorte 2005')
    page.get_by_label('Tout l’historique').check();expect(section).to_contain_text('Cohorte 2005')
    expect(section.get_by_role('table').first).to_contain_text('Moyenne avril–sept. 2005')
    download=page.request.get('http://dashboard:8052/download/macro.csv');csv_ok=download.ok and 'cohort_window_mean' in download.text()
    page.evaluate(Path('/opt/axe.min.js').read_text())
    axe=page.evaluate("async () => await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
    section.screenshot(path=str(out/'macro-desktop.png'))
    mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True);mobile.goto('http://dashboard:8052/#macro',wait_until='networkidle')
    expect(mobile.locator('#macro').locator('..').locator('.js-plotly-plot .gtitle')).to_contain_text('Retards',timeout=30000)
    report={'event':'macro_browser_checks','series_switch':True,'period_switch_hides_2005_window_on_5_years':True,'summary_table':True,'csv_download':csv_ok,
            'axe_violations':[{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in axe['violations']],'axe_incomplete':len(axe['incomplete']),
            'mobile_global_overflow':mobile.evaluate('document.documentElement.scrollWidth > innerWidth + 1'),'console_errors':errors}
    mobile.locator('#macro').locator('..').screenshot(path=str(out/'macro-mobile.png'))
    report['screenshots']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('macro-*.png')}
    (out/'macro-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));browser.close()
    assert csv_ok and not errors and not report['axe_violations'] and not report['mobile_global_overflow']
