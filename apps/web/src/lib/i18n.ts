export type Locale = "en" | "fr";

const copy = {
  en: {
    eyebrow: "Montreal return pickup",
    hero: "Your return, already on its way.",
    sub: "Choose a pickup window. We collect your prepared package and deliver it to the authorized return point—with proof at every handoff.",
    book: "Book a pickup",
    track: "Track a return",
    window: "Confirmed window",
    estimate: "Estimated arrival",
    promise: "Estimates update with traffic. Your confirmed window is the commitment.",
    prep: "Prepare your return",
    prepBody: "Authorize the return with the retailer, seal the package, and attach the valid label before pickup.",
    route: "We pick it up",
    routeBody: "A verified driver scans the package and records custody evidence.",
    proof: "Proof to the finish",
    proofBody: "See the receipt or handoff reference after delivery to the carrier or retailer.",
    admin: "Operations console",
    role: "Local demo role",
    active: "Active work",
    risks: "Needs attention",
    routes: "Route proposals",
    empty: "No urgent exceptions. New risks will appear here.",
    footer: "Returnet does not control retailer refund approval or timing."
  },
  fr: {
    eyebrow: "Ramassage de retours à Montréal",
    hero: "Votre retour est déjà en route.",
    sub: "Choisissez une plage de ramassage. Nous récupérons votre colis préparé et le livrons au point de retour autorisé, avec une preuve à chaque remise.",
    book: "Réserver un ramassage",
    track: "Suivre un retour",
    window: "Plage confirmée",
    estimate: "Arrivée estimée",
    promise: "L’estimation évolue selon la circulation. La plage confirmée demeure notre engagement.",
    prep: "Préparez votre retour",
    prepBody: "Autorisez le retour auprès du détaillant, fermez le colis et apposez l’étiquette valide avant le ramassage.",
    route: "Nous le ramassons",
    routeBody: "Un chauffeur vérifié numérise le colis et consigne la prise en charge.",
    proof: "Une preuve jusqu’au bout",
    proofBody: "Consultez le reçu ou la référence après la remise au transporteur ou au détaillant.",
    admin: "Console des opérations",
    role: "Rôle de démonstration local",
    active: "Travail actif",
    risks: "À surveiller",
    routes: "Propositions de tournée",
    empty: "Aucune exception urgente. Les nouveaux risques apparaîtront ici.",
    footer: "Returnet ne contrôle ni l’approbation ni le délai du remboursement du détaillant."
  }
} as const;

export function messages(locale: Locale) {
  return copy[locale];
}

