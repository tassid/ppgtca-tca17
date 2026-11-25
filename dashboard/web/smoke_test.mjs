// Abre o site estático num navegador e confere se as telas carregam sem erro.
// Uso: node smoke_test.mjs http://localhost:8000
import { chromium } from "playwright";

const base = process.argv[2] ?? "http://localhost:8000";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
const erros = [];
page.on("pageerror", (e) => erros.push(e.message));
page.on("console", (m) => { if (["error", "warning"].includes(m.type())) console.log(`[console ${m.type()}] ${m.text().slice(0, 400)}`); });

async function confere(url, texto, arquivo) {
  await page.goto(url);
  try {
    await page.getByText(texto).first().waitFor({ timeout: 240_000 });
  } catch (e) {
    await page.screenshot({ path: `capturas/falha_${arquivo}`, fullPage: true });
    console.log("Texto da página na falha:\n" + (await page.locator("body").innerText()).slice(0, 3000));
    throw e;
  }
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `capturas/${arquivo}`, fullPage: true });
  const exc = await page.locator('[data-testid="stException"]').count();
  if (exc) throw new Error(`${url}: ${exc} erro(s) do Python na tela`);
  console.log(`ok  ${url}`);
}

await confere(`${base}/`, "Planejamento da safra", "1_planejamento.png");
await confere(`${base}/?modo=totem&unidade=U20`, "Tenho agendamento", "2_totem.png");
await page.getByRole("button", { name: /Não tenho agendamento/ }).click();
await page.getByText("Horário").first().waitFor({ timeout: 60_000 });
await page.screenshot({ path: "capturas/3_totem_agendar.png", fullPage: true });
console.log("ok  totem, tela de agendamento");

await browser.close();
if (erros.length) console.log("Avisos do navegador:\n" + erros.join("\n"));
