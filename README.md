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

- **Miljökontrakt** ([docs/environment-contract.md](docs/environment-contract.md)): modellen skriver
  själv svaret (belopp, datum, JSON, stränglistor) eller arbetar med verktyg i flera steg och bedöms på
  systemets slutläge. Ingen flervalsfråga.
- **Kontoret** ([docs/kontoret.md](docs/kontoret.md)): en gemensam syntetisk svensk organisation med personal,
  kunder, fakturor, inbetalningar, OCR, bankgiro, organisationsnummer, moms och svenska röda dagar.
- Åtta miljöer:

| Miljö | Typ | Arbetsuppgift |
|---|---|---|
| `invoice_amount_due` | belopp | Belopp att betala: blandad moms, rabatter, delbetalning, kreditnota, avrundning; ibland saknas information |
| `payment_matching` | JSON | Matcha inbetalningar mot fakturor med OCR-kontroll och reservregel |
| `meeting_slot` | datum och tid | Första gemensamma mötestid med röda dagar, lunch och buffertregel |
| `document_redaction` | stränglista | Maskera personuppgifter enligt en policy inför utlämnande |
| `payment_registration` | verktyg | Registrera inbetalningar i reskontran och mejla om restbelopp |
| `meeting_reschedule` | verktyg | Flytta ett möte när någon fått förhinder och meddela deltagarna |
| `supplier_quotes` | JSON | Välj leverantör utifrån pris, frakt, kapacitet, leveranstid och budget, eller avstå |
| `inventory_reorder` | JSON | Beställningsförslag med reservationer, inkommande leveranser och förpackningsstorlek |

- Kontraktskvalificering med **genvägsprober**: tomma svar, kopierade tal, att alltid avstå eller att bara läsa
  med verktyg får inte löna sig.
- Export till RL-träningsdata (`svrl.cli export`, `export-hf` med taggen `rl-environment`) och en
  rollout-körare för valfri OpenAI-kompatibel modell (`svrl.cli rollout`: vLLM, Ollama, llama.cpp).
- 100 uppgiftsspecifikationer över 20 arbetsområden, skrivna för miljökontraktet, och en planeringsram för
  **20 000** miljöer. Det är ett mål, inte färdiga miljöer.
- Automatiska 24-timmarsanspråk genom `/claim`, `/renew` och `/release` i issues.

## Evidensnivåer

| Nivå | Krav | Betydelse |
|---|---|---|
| Kontrakt | `svrl.cli check`: determinism, referenssvar får 1, genvägsprober får högst 0,3, oberoende domäntester | Miljön fungerar och går inte att lura på enkla sätt (körs i CI) |
| L1 · Baslinje | `svrl.cli rollout` med en låst modell på eval-delen | Visar hur svår miljön är och om den lämnar utrymme att lära |
| L2 · Tränad | Modell på minst 100M parametrar, RL-uppdateringar, ändrade vikter och ändlig loss/gradientkurva | Träning faktiskt körd; minskande loss krävs inte i policygradient-RL |
| L3 · Förbättrad | Matchad held-out-eval, minst +5 procentenheter och positiv nedre 95%-bootstrapgräns | Förbättring i experimentet; oberoende replikation behövs för betrodd märkning |

L2/L3 körs på bidragsgivarens beräkningsresurser. En agent bygger och testar;
bidragsgivaren behöver inte skriva kod eller granska för hand. Automatisk
sammanslagning och betrodd resultatsignering är kommande infrastrukturarbete.

## Kör lokalt

Python 3.9+ räcker för miljöer, kontraktstester och export.

```bash
git clone https://github.com/BirgerMoell/svenska-rl.git
cd svenska-rl
python3 -m svrl.cli list
python3 -m svrl.cli demo payment_registration
python3 -m svrl.cli check invoice_amount_due
python3 -m unittest discover -s tests -v
node --test tests/claims.test.cjs
```

Baslinje mot en lokal modell, till exempel via Ollama:

```bash
python3 -m svrl.cli rollout meeting_reschedule --base-url http://127.0.0.1:11434/v1 --model <modell> --count 32
```

Träningsdata: `python3 -m svrl.cli export invoice_amount_due --split train --count 5000 --out data/train.jsonl`.
Baslinjer, träning och före/efter-jämförelse: [beräkningsbidrag](docs/compute.md).

## För agenter

- [Starta ett bidrag](.agents/skills/contribute-svenska-rl/SKILL.md)
- [Miljökontrakt](docs/environment-contract.md)
- [Kontoret](docs/kontoret.md)
- [Definition of done](docs/validation.md)
- [Beräkningsbidrag](docs/compute.md)
- [Katalog och färdplan](docs/catalogue.md)
- [Bidragsinstruktioner](CONTRIBUTING.md)

Inspirerat av [OpenEnv](https://github.com/openenv/OpenEnv),
[FinQA](https://huggingface.co/docs/openenv/en/environments/finqa) och NeMo Gym:s Workplace Assistant.
Kontrakten är lokala; en OpenEnv-adapter finns ännu inte.
FinQA:s utvärderingsdata används inte för träning.

Kod och egna syntetiska mallar: Apache-2.0, se [LICENSE](LICENSE).
