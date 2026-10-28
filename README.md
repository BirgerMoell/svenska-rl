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

- **Kontrakt v0.2** ([docs/environment-contract-v0.2.md](docs/environment-contract-v0.2.md)): modellen skriver
  själv svaret (belopp, datum, JSON, stränglistor) eller arbetar med verktyg i flera steg och bedöms på
  systemets slutläge. Ingen flervalsfråga.
- **Kontoret** ([docs/kontoret.md](docs/kontoret.md)): en gemensam syntetisk svensk organisation med personal,
  kunder, fakturor, inbetalningar, OCR, bankgiro, organisationsnummer, moms och svenska röda dagar.
- Sex miljöer enligt v0.2:

| Miljö | Typ | Arbetsuppgift |
|---|---|---|
| `invoice_amount_due` | belopp | Belopp att betala: blandad moms, rabatter, delbetalning, kreditnota, avrundning; ibland saknas information |
| `payment_matching` | JSON | Matcha inbetalningar mot fakturor med OCR-kontroll och reservregel |
| `meeting_slot` | datum och tid | Första gemensamma mötestid med röda dagar, lunch och buffertregel |
| `document_redaction` | stränglista | Maskera personuppgifter enligt en policy inför utlämnande |
| `payment_registration` | verktyg | Registrera inbetalningar i reskontran och mejla om restbelopp |
| `meeting_reschedule` | verktyg | Flytta ett möte när någon fått förhinder och meddela deltagarna |

- Kontraktskvalificering med **genvägsprober**: tomma svar, kopierade tal, att alltid avstå eller att bara läsa
  med verktyg får inte löna sig.
- Export till RL-träningsdata (`svrl.cli export`, `export-hf` med taggen `rl-environment`) och en
  rollout-körare för valfri OpenAI-kompatibel modell (`svrl.cli rollout`: vLLM, Ollama, llama.cpp).
- De tre första flervalsmiljöerna (kontrakt v0.1) finns kvar som startexempel.
- 100 uppgiftsspecifikationer över 20 arbetsområden, nu skrivna för kontrakt v0.2, och en planeringsram för
  **20 000** miljöer. Det är ett mål, inte färdiga miljöer.
- Automatiska 24-timmarsanspråk genom `/claim`, `/renew` och `/release` i issues.

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
Flervalsmiljöerna (v0.1) har kvar L1/L2-vägen i [träningsinstruktionerna](docs/compute.md).

## För agenter

- [Starta ett bidrag](.agents/skills/contribute-svenska-rl/SKILL.md)
- [Miljökontrakt v0.2](docs/environment-contract-v0.2.md) (och [v0.1](docs/environment-contract.md))
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
