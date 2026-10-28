"""Maskera personuppgifter i ett ärende enligt en uttrycklig policy (inför utlämnande av allmän handling).

A synthetic case message mixes private persons' data (identity numbers, mobile numbers, private e-mail
addresses, home addresses) with information that must stay readable (the organisation's own switchboard number
and functional mailbox, organisation numbers, case numbers, officials' names). The policy sentence varies by
task, e.g. officials' names may or may not be masked, so the model must read the policy. Answer: a JSON list of
the exact strings to mask, in order of appearance, with repeats. Partial reward = multiset F1.
"""
from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret import ids
from svrl.kontoret.world import World

STREETS = ["Storgatan", "Kyrkvägen", "Skolgatan", "Björkvägen", "Parkvägen", "Ringvägen", "Södra Långgatan", "Åsvägen"]

POLICIES = {
    "id_phone_email": ("Maskera privatpersoners personnummer, mobilnummer och privata e-postadresser. Allt annat "
                       "ska stå kvar, även namn och adresser.", {"id", "phone", "email"}),
    "all_contact": ("Maskera privatpersoners personnummer, mobilnummer, privata e-postadresser och "
                    "hemadresser (gatuadress med nummer). Namn ska stå kvar.", {"id", "phone", "email", "address"}),
    "with_names": ("Maskera privatpersoners namn, personnummer, mobilnummer och privata e-postadresser. "
                   "Handläggares namn och myndighetens egna kontaktuppgifter ska stå kvar.",
                   {"name", "id", "phone", "email"}),
}


class DocumentRedaction(TypedEnvironment):
    id = "document_redaction"
    partial_reward = True

    def generate(self, rng):
        world = World(rng)
        policy_id = rng.choice(sorted(POLICIES))
        policy, classes = POLICIES[policy_id]
        official = world.staff[0]
        applicant, other = world.person(), world.person()
        while other.name == applicant.name:
            other = world.person()
        case = f"{rng.choice(['KS', 'SN', 'BN', 'UN'])} {world.today.year}/{rng.randint(100, 2999)}"
        private_mail = f"{applicant.first.lower()}{rng.randint(10, 99)}@{rng.choice(['mejl.se', 'post.nu', 'brev.com'])}"
        private_mail = private_mail.translate(str.maketrans("åäöé", "aaoe"))
        address = f"{rng.choice(STREETS)} {rng.randint(1, 80)}"
        org_mail = f"registrator@{world.org.name.split()[0].lower().translate(str.maketrans('åäöé', 'aaoe'))}.se"
        switchboard = f"010-{rng.randint(100, 999)} {rng.randint(10, 99)} {rng.randint(10, 99)}"
        segments = [  # (text, class or None)
            ("Ärende ", None), (case, None), ("\nHandläggare: ", None), (official.name, None),
            (f", {world.org.name}, organisationsnummer ", None), (world.org.org_number, None), ("\n\n", None),
            ("Inkommande brev från ", None), (applicant.name, "name"), (" (personnummer ", None),
            (applicant.id_number, "id"), ("), bosatt på ", None), (address, "address"), (". ", None),
            ("Jag nås på ", None), (applicant.phone, "phone"), (" eller ", None), (private_mail, "email"),
            (". Jag ansöker om bostadsanpassning och bifogar intyg. Min granne ", None), (other.name, "name"),
            (" har lovat att hjälpa till och kan nås på ", None), (other.phone, "phone"), (".\n\n", None),
            ("Svar från handläggaren: Tack ", None), (applicant.first, "name"),
            ("! Vi har registrerat ansökan. Frågor besvaras via vår växel ", None), (switchboard, None), (" eller ", None), (org_mail, None),
            (". Hälsningar, ", None), (official.name, None), ("\n", None),
        ]
        if rng.random() < .5:  # the applicant's id number repeated in a reference line
            segments += [("Referens i e-tjänsten: ", None), (applicant.id_number, "id"), ("\n", None)]
        text = "".join(t for t, _ in segments)
        expected = [t for t, c in segments if c in classes]
        instruction = (f"Du ska förbereda ett ärende för utlämnande. Policy: {policy}\n"
                       "Ange vilka textsträngar som ska maskeras.\n\n--- ÄRENDE ---\n" + text + "--- SLUT ---")
        assert ids.luhn_valid(applicant.id_number)
        return TypedTask(instruction, {"type": "strings", "value": expected}, "strings",
                         {"policy": policy_id, "items": len(expected)})


def create():
    return DocumentRedaction()
