# Svenska RL

**Låt din kodagent bidra till öppna AI-modeller på svenska.**

Ge din agent en enda länk: **https://birgermoell.github.io/svenska-rl/**

> Läs agentinstruktionerna på länken. Välj en ledig uppgift, gör anspråk på den,
> bygg och testa miljön, och skicka en pull request. Har jag lämplig lokal
> beräkningskapacitet kan du också köra träning och utvärdering inom min budget.

Ingen skill-installation behövs: sidan länkar till ett komplett
[SKILL.md](.agents/skills/contribute-svenska-rl/SKILL.md) som kodagenten kan läsa.
En webblänk installerar inte automatiskt en skill i agentens konfiguration.

## Vad finns nu?

- Tre körbara svenska referensmiljöer: fakturaberäkning, kalenderbokning och lagerbeställning.
- 100 startuppgifter, fem per arbetsområde, och 200 arbetsflödesfrön. De 80 nya
  specifikationerna anger indata, mål, verifierare, gränsfall och eval.
- En planeringsram för **20 000** miljöer. Dessa är ett mål, inte färdiga miljöer.
- Automatiska 24-timmarsanspråk genom `/claim`, `/renew` och `/release` i issues.
- Kontraktstester, en liten neural modell för L1 och en Hugging Face-tränare för L2/L3.
- GitHub Actions för tester, L1 och publicering av agentsidan.

## Tre nivåer av evidens

| Nivå | Krav | Betydelse |
|---|---|---|
| L1 · Körbar | Kontrakt, verifierartester och liten neural policy genomför episoder | Funktion kontrollerad; ingen inlärning påstås |
| L2 · Tränad | Modell på minst 100M parametrar, RL-uppdateringar, ändrade vikter och ändlig loss/gradientkurva | Träning faktiskt körd; minskande loss krävs inte i policygradient-RL |
| L3 · Förbättrad | Matchad held-out-eval, minst +5 procentenheter och positiv nedre 95%-bootstrapgräns | Förbättring i experimentet; oberoende replikation behövs för betrodd märkning |

L2/L3 körs på bidragsgivarens beräkningsresurser. En agent bygger och testar;
bidragsgivaren behöver inte skriva kod eller granska för hand. Automatisk
sammanslagning och betrodd resultatsignering är kommande infrastrukturarbete.

## Kör lokalt

Python 3.9+ räcker för miljöer och kontraktstester.

```bash
git clone https://github.com/BirgerMoell/svenska-rl.git
cd svenska-rl
python3 -m svrl.cli list
python3 -m svrl.cli demo invoice_totals
python3 -m svrl.cli check invoice_totals
python3 -m unittest discover -s tests -v
node --test tests/claims.test.cjs
```

Med PyTorch: `python3 -m svrl.cli smoke invoice_totals --output runs/invoice-l1.json`.
För språkmodellsträning: följ [träningsinstruktionerna](docs/compute.md).

## För agenter

- [Starta ett bidrag](.agents/skills/contribute-svenska-rl/SKILL.md)
- [Miljökontrakt](docs/environment-contract.md)
- [Definition of done](docs/validation.md)
- [Beräkningsbidrag](docs/compute.md)
- [Katalog och färdplan](docs/catalogue.md)
- [Bidragsinstruktioner](CONTRIBUTING.md)

Inspirerat av [OpenEnv](https://github.com/openenv/OpenEnv) och
[FinQA](https://huggingface.co/docs/openenv/en/environments/finqa). Det första
kontraktet är lokalt och single-turn; det är inte ännu en OpenEnv-adapter.
FinQA:s utvärderingsdata används inte för träning.

Kod och egna syntetiska mallar: Apache-2.0, se [LICENSE](LICENSE).
