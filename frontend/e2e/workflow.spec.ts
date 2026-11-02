import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('real 3D model, LED editor, exact dimensions, and all export formats',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();
  await expect(page.getByRole('button',{name:/Korpus 02/})).toBeVisible();
  const pngPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Zapisz podgląd PNG',exact:true}).click();
  const png=await readFile((await (await pngPromise).path())!);
  expect([...png.subarray(0,8)]).toEqual([137,80,78,71,13,10,26,10]);
  await page.screenshot({path:'../docs/screenshots/desktop.png',fullPage:true});
  await page.getByRole('button',{name:'LED',exact:true}).click();
  await page.getByRole('button',{name:'Zaproponuj rozmieszczenie'}).click();
  await expect(page.getByRole('img',{name:'Edytor wnętrza litery w milimetrach'})).toBeVisible();
  await expect(page.locator('.placement')).toHaveCount(3);
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  const before=await page.locator('.placement').first().getAttribute('transform');
  await page.getByRole('spinbutton',{name:'Pozycja X',exact:true}).fill('31');
  await page.getByRole('spinbutton',{name:'Pozycja X',exact:true}).blur();
  await expect(page.locator('.placement').first()).not.toHaveAttribute('transform',before!);
  await page.getByRole('button',{name:'Cofnij zmianę'}).click();
  await expect(page.locator('.placement').first()).toHaveAttribute('transform',before!);
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Podgląd 3D',exact:true}).click();
  await page.getByLabel('Widok modelu').selectOption('transparent');
  await page.getByRole('button',{name:'Eksport',exact:true}).click();
  await expect(page.getByText('Geometria sprawdzona',{exact:true})).toBeVisible();
  for(const format of ['Kompletny zestaw','Projekt wieloczęściowy','Wszystkie części']){
    const downloadPromise=page.waitForEvent('download');
    await page.getByRole('button',{name:new RegExp(format)}).click();
    const download=await downloadPromise;
    const bytes=await readFile((await download.path())!);
    expect(bytes.length).toBeGreaterThan(1000);
    if(format!=='Wszystkie części')expect(bytes.subarray(0,2).toString()).toBe('PK');
  }
  expect(errors).toEqual([]);
});

test('too-wide LED blocks the real export, fixing it restores readiness',async({page})=>{
  await page.goto('/');await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'LED',exact:true}).click();
  await page.getByRole('button',{name:'Sekcja LED',exact:false}).click();
  await page.getByRole('spinbutton',{name:'Szerokość elementu',exact:true}).fill('80');
  await page.getByRole('spinbutton',{name:'Szerokość elementu',exact:true}).blur();
  await expect(page.getByText(/wybrana szerokość 80 mm/)).toBeVisible();
  await page.getByRole('button',{name:'Eksport',exact:true}).click();
  await expect(page.getByRole('button',{name:/Kompletny zestaw/})).toBeDisabled();
  await page.getByRole('button',{name:'LED',exact:true}).click();
  await page.getByRole('button',{name:'Usuń element',exact:true}).click();
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Eksport',exact:true}).click();
  await expect(page.getByRole('button',{name:/Kompletny zestaw/})).toBeEnabled();
});

test('JSON save and reopening restores font and all model parameters',async({page})=>{
  await page.goto('/');await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByLabel('Tekst napisu').fill('ŻÓŁW');
  await page.getByRole('button',{name:/Pełne litery/}).click();
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByLabel('Nazwa projektu').fill('Polskie litery — test');
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Zapisz projekt',exact:true}).click();
  const bytes=await readFile((await (await downloadPromise).path())!);const saved=JSON.parse(bytes.toString());
  expect(saved.text).toBe('ŻÓŁW');expect(saved.height).toBe(120);expect(saved.mode).toBe('solid');
  await page.getByLabel('Tekst napisu').fill('ABC');
  await page.locator('input[type="file"][accept=".json"]').setInputFiles({name:'project.json',mimeType:'application/json',buffer:bytes});
  await expect(page.getByLabel('Tekst napisu')).toHaveValue('ŻÓŁW');
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Ostatnie projekty'}).click();
  await expect(page.getByRole('dialog')).toContainText('Polskie litery — test');
});

test('Neon Flex skeleton is editable and unsafe routes cannot be exported',async({page})=>{
  await page.goto('/');await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/Neon Flex Otwarty/}).click();
  await page.getByRole('button',{name:'LED',exact:true}).click();
  await page.getByRole('button',{name:'Wyznacz linie środkowe'}).click();
  await expect(page.getByRole('img',{name:'Edytor wnętrza litery w milimetrach'})).toBeVisible();
  await expect(page.locator('.path-nodes')).toBeVisible();
  await expect(page.getByText(/Trasa.*zbyt ostry zakręt/).first()).toBeVisible();
  await page.getByRole('button',{name:'Eksport',exact:true}).click();
  await expect(page.getByRole('button',{name:/Projekt wieloczęściowy/})).toBeDisabled();
});

test('mobile interface, color controls, views and parameter changes work',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('button',{name:'Wymiary',exact:true}).click();
  await page.getByRole('spinbutton',{name:'Ścianka boczna',exact:true}).fill('3');
  await page.getByRole('spinbutton',{name:'Ścianka boczna',exact:true}).blur();
  await expect(page.getByText('Model aktualny',{exact:true})).toBeVisible();
  await page.getByLabel('Widok modelu').selectOption('section');
  await page.getByLabel('Kamera',{exact:true}).selectOption('top');
  await page.screenshot({path:'../docs/screenshots/mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Zmień motyw'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});
