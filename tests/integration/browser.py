"""Vrai navigateur : filtres, clavier, marché, mobile et axe, sans résultat inventé."""
from pathlib import Path
import json,hashlib
from playwright.sync_api import sync_playwright,expect
out=Path('/evidence');out.mkdir(exist_ok=True,parents=True)
with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://dashboard:8052/',wait_until='networkidle');expect(page.locator('#filter-status')).to_have_text('30000 observations dans la sélection.',timeout=30000)
    page.keyboard.press('Tab');expect(page.get_by_role('link',name='Aller au contenu')).to_be_focused();page.keyboard.press('Enter')
    page.locator('#age-min').fill('50');page.locator('#age-min').press('Tab')
    page.locator('#age-max').fill('60');page.locator('#age-max').press('Tab')
    ref=json.loads(Path('/reference/browser-reference.json').read_text())
    expect(page.locator('#filter-status')).to_have_text(str(ref['age_50_60_count'])+' observations dans la sélection.',timeout=15000)
    page.locator('#age-min').fill('80');page.locator('#age-min').press('Tab');expect(page.locator('#filter-status')).to_contain_text('Filtres invalides')
    page.locator('#age-min').fill('0');page.locator('#age-min').press('Tab');page.locator('#age-max').fill('120');page.locator('#age-max').press('Tab');expect(page.locator('#filter-status')).to_have_text('30000 observations dans la sélection.')
    page.locator('#segment').locator('..').locator('.dash-dropdown-focus-target').focus();page.keyboard.press('ArrowDown');page.keyboard.press('Escape')
    page.get_by_text('Drawdown',exact=True).first.click();expect(page.locator('#market-table')).to_contain_text('Drawdown')
    page.get_by_role('button',name='Risques',exact=True).click();expect(page.locator('#audience-result')).to_contain_text('2063 fausses alertes')
    page.get_by_role('button',name='Analyse de données',exact=True).click();expect(page.locator('#audience-result')).to_contain_text('groupes de profils séparés')
    page.get_by_role('button',name='Générer une synthèse à relire').click();expect(page.locator('#generation-result')).to_contain_text('Brouillon à relire',timeout=120000)
    page.evaluate(Path('/opt/axe.min.js').read_text())
    axe=page.evaluate("async () => await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
    report={'event':'browser_checks','filter_reference_rows':ref['age_50_60_count'],'keyboard_skip':True,'invalid_filter_message':True,'market_switch':True,'role_views':True,'real_llm_callback':True,'axe_violations':[{'id':v['id'],'impact':v['impact'],'description':v['description'],'nodes':[n['target'] for n in v['nodes']]} for v in axe['violations']],'axe_incomplete':len(axe['incomplete']),'console_errors':errors}
    page.screenshot(path=str(out/'dashboard-desktop.png'),full_page=True)
    mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True);mobile.goto('http://dashboard:8052/',wait_until='networkidle');expect(mobile.locator('#filter-status')).to_have_text('30000 observations dans la sélection.',timeout=30000)
    report['mobile_global_overflow']=mobile.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    mobile.screenshot(path=str(out/'dashboard-mobile.png'),full_page=True)
    report['screenshots']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('dashboard-*.png')};report['axe_script_sha256']=hashlib.sha256(Path('/opt/axe.min.js').read_bytes()).hexdigest()
    (out/'browser-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));browser.close()
    assert not errors and not report['axe_violations'] and not report['mobile_global_overflow']
